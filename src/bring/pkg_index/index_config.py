# -*- coding: utf-8 -*-
import collections
import logging
import os
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Union

from bring.defaults import BRING_CONTEXT_NAMESPACE, BRING_DEFAULT_CONTEXTS
from bring.pkg_index import BringIndexTing
from bring.pkg_index.folder_index import BringDynamicIndexTing
from bring.pkg_index.static_index import BringStaticIndexTing
from bring.utils.indexes import validate_index_name
from bring.utils.system_info import get_current_system_info
from frtls.dicts import dict_merge, get_seeded_dict
from frtls.exceptions import FrklException
from frtls.formats.input_formats import (
    INPUT_FILE_TYPE,
    SmartInput,
    determine_input_file_type,
)
from frtls.strings import is_git_repo_url
from tings.tingistry import Tingistry


log = logging.getLogger("bring")


class BringIndexConfig(metaclass=ABCMeta):

    _plugin_type = "instance"

    @classmethod
    def auto_parse_config_string(
        cls, config_string: str, index_name: Optional[str] = None
    ) -> Dict[str, Any]:

        if "=" in config_string and not index_name:
            index_name, config_string = config_string.split("=", maxsplit=1)

        if config_string in BRING_DEFAULT_CONTEXTS.keys():
            if not index_name:
                index_name = config_string
            _default_index: Mapping[str, Any] = BRING_DEFAULT_CONTEXTS[
                config_string
            ]  # type: ignore
            _init_data: Dict[str, Any] = dict(_default_index)
            _init_data["name"] = index_name
        elif config_string.endswith(".br.idx"):
            if not index_name:
                index_name = os.path.basename(config_string[0:7])
            _init_data = {
                "name": index_name,
                "type": "index",
                "indexes": [config_string],
                "_name_autogenerated": True,
            }
        elif os.path.isdir(config_string) or is_git_repo_url(config_string):

            if is_git_repo_url(config_string):
                raise NotImplementedError()

            config_string = os.path.abspath(config_string)

            if config_string.endswith(os.path.sep):
                config_string = config_string[0:-1]

            if index_name is None:
                if os.path.isdir(config_string):
                    _name = os.path.basename(config_string)
                else:
                    _name = config_string.split("/")[-1]

                if _name.endswith(".git"):
                    _name = _name[0:-4]
                index_name = _name
            _init_data = {
                "name": index_name,
                "type": "folder",
                "indexes": [config_string],
                "_name_autogenerated": True,
            }
        else:
            raise FrklException(
                msg=f"Can't create index for: {config_string}",
                reason="String is not a index alias, folder, or git url.",
            )

        if index_name is not None:
            _init_data["name"] = index_name
            _init_data["_name_generated"] = False

        return _init_data

    @classmethod
    def create(
        cls,
        tingistry_obj: Tingistry,
        init_data: Union[str, Mapping[str, Any]],
        index_name: Optional[str] = None,
    ):

        if isinstance(init_data, str):
            init_data = cls.auto_parse_config_string(init_data, index_name=index_name)

        config_type = init_data["type"]
        pm = tingistry_obj.typistry.get_plugin_manager(BringIndexConfig)

        config_type_cls = pm.get_plugin(config_type)

        if config_type_cls is None:
            raise FrklException(
                msg=f"Can't create index config of type '{config_type}'.",
                reason="No plugin registered for this type.",
            )
        config = config_type_cls(tingistry_obj=tingistry_obj, init_data=init_data)

        return config

    def __init__(
        self,
        tingistry_obj: Tingistry,
        init_data: Mapping[str, Any],
        global_defaults: Optional[Mapping[str, Any]] = None,
    ):

        self._tingistry_obj = tingistry_obj
        # if isinstance(init_data, str):
        #     _init_data: Dict[str, Any] = BringIndexConfig.auto_parse_config_string(
        #         config_string=init_data
        #     )
        # else:
        #     if len(init_data) == 1 and list(init_data.keys())[0] not in [
        #         "name",
        #         "type",
        #     ]:
        #         index_name = list(init_data.keys())[0]
        #         config_string = init_data[index_name]
        #         _init_data = BringIndexConfig.auto_parse_config_string(
        #             config_string, index_name=index_name
        #         )
        #     else:
        #         _init_data = dict(init_data)
        _init_data = dict(init_data)
        self._name: str = _init_data.pop("name")
        self._type: str = _init_data.pop("type")
        self._name_autogenerated: bool = _init_data.pop("_name_autogenerated", False)
        self._init_data: Mapping[str, Any] = _init_data

        if global_defaults is None:
            global_defaults = {}
        self._global_defaults: MutableMapping[str, Any] = dict(global_defaults)

        self._index: Optional[BringIndexTing] = None

        self._extra_data: Optional[Mapping[str, Any]] = None
        self._config_dict: Optional[Mapping[str, Any]] = None

    @property
    def name(self) -> str:

        return self._name

    @name.setter
    def name(self, name: str) -> None:

        if not self._name_autogenerated:
            raise FrklException(
                msg=f"Can't change name of index '{self._name}'.",
                reason="Name not autogenerated.",
            )

        self._name = name

    @property
    def type(self) -> str:

        return self._type

    @property
    def init_data(self) -> Mapping[str, Any]:

        return self._init_data

    @property
    async def extra_data(self) -> Mapping[str, Any]:

        if self._extra_data is not None:
            return self._extra_data

        self._extra_data = await self.get_extra_data()
        return self._extra_data

    @abstractmethod
    async def get_extra_data(self) -> Mapping[str, Any]:
        """A method to retrieve config type specific index metadata/config."""

        pass

    async def get_raw_config(self) -> Dict[str, Any]:

        extra_data = await self.extra_data
        config_dict = get_seeded_dict(
            extra_data, self.init_data, merge_strategy="merge"
        )

        return config_dict  # type: ignore

    @property
    async def config_dict(self) -> Mapping:

        if self._config_dict is not None:
            return self._config_dict

        config_dict = await self.get_raw_config()

        defaults = config_dict.get("defaults", {})
        if not self._global_defaults:
            _defaults: Mapping[str, Any] = defaults
        else:
            _defaults = dict_merge(self._global_defaults, defaults, copy_dct=False)
        config_dict["defaults"] = _defaults

        if "vars" not in config_dict["defaults"].keys():
            config_dict["defaults"]["vars"] = {}
        elif not isinstance(config_dict["defaults"]["vars"], collections.Mapping):
            raise FrklException(
                f"Invalid config, 'vars' key in 'defaults' index property needs to be a mapping: {config_dict['defaults']['vars']}"
            )

        if config_dict.get("add_sysinfo_to_default_vars", False):
            for k, v in get_current_system_info().items():
                if k not in config_dict["defaults"]["vars"].keys():
                    config_dict["defaults"]["vars"][k] = v

        self._config_dict = config_dict
        return self._config_dict

    async def to_dict(self) -> Dict[str, Any]:

        result = dict(await self.config_dict)
        result["name"] = self.name
        result["type"] = self.type

        if self._name_autogenerated:
            result["_name_autogenerated"] = self._name_autogenerated

        return result

    async def get_index(self) -> BringIndexTing:

        if self._index is None:
            # config_dict = await self.to_dict()
            self._index = await self.create_index()
        return self._index

    @abstractmethod
    async def create_index(self) -> BringIndexTing:

        pass


class FolderIndexConfig(BringIndexConfig):

    _plugin_name = "folder"

    async def get_extra_data(self) -> Mapping[str, Any]:

        config_overlays: List[Mapping[str, Any]] = []
        full_indexes = []
        for dir in self.init_data["indexes"]:
            full_indexes.append(os.path.abspath(dir))
            index_metadata = os.path.join(dir, ".bring_index")

            if os.path.isfile(index_metadata):
                si = SmartInput(index_metadata)
                try:
                    content = await si.content_async()
                    config_overlays.append(content)
                except Exception as e:
                    log.error(
                        f"Can't read index metadata file '{index_metadata}', ignoring it. Error: {e}"
                    )
                    log.error(f"Error: {e}", exc_info=True)

        if config_overlays:
            config = get_seeded_dict(*config_overlays, merge_strategy="update")
        else:
            config = {}

        return config

    async def create_index(self) -> BringIndexTing:

        config_dict = await self.config_dict
        indexes = list(config_dict["indexes"])
        if len(indexes) != 1:
            raise NotImplementedError()

        folder = indexes[0]
        input_type = determine_input_file_type(folder)

        # if input_type == INPUT_FILE_TYPE.git_repo:
        #     git_url = expand_git_url(path, DEFAULT_URL_ABBREVIATIONS_GIT_REPO)
        #     _path = await ensure_repo_cloned(git_url)
        if input_type == INPUT_FILE_TYPE.local_dir:
            if isinstance(folder, Path):
                _path: str = os.path.realpath(folder.resolve().as_posix())
            else:
                _path = os.path.realpath(os.path.expanduser(folder))
        else:
            raise FrklException(
                msg=f"Can't add index for: {folder}.",
                reason=f"Invalid input file type {input_type}.",
            )

        validate_index_name(self._name)
        ctx: BringDynamicIndexTing = self._tingistry_obj.create_ting(  # type: ignore
            "bring_dynamic_index_ting", f"{BRING_CONTEXT_NAMESPACE}.{self._name}"
        )
        _ind = [_path]
        ctx_config = await self.to_dict()
        ctx_config["indexes"] = _ind
        ctx.set_input(  # type: ignore
            ting_dict=ctx_config
        )

        await ctx.get_values("config")

        return ctx


class IndexIndexConfig(BringIndexConfig):

    _plugin_name = "index"

    async def get_extra_data(self) -> Mapping[str, Any]:

        return {}

    async def create_index(self) -> BringIndexTing:

        ctx: BringStaticIndexTing = self._tingistry_obj.create_ting(  # type: ignore
            "bring.types.indexes.default_index",
            f"{BRING_CONTEXT_NAMESPACE}.{self._name}",
        )

        ctx_config = await self.to_dict()

        ctx.set_input(ting_dict=ctx_config)
        await ctx.get_values("config")

        return ctx
