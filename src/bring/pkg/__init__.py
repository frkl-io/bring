import atexit
import collections
import json
import os
import shutil
from abc import ABCMeta, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Mapping, Any, Optional, Iterable, Union, Dict, List, Sequence

from deepdiff import DeepHash
from tzlocal import get_localzone

from anyio import open_file

from bring.defaults import BRING_PKG_INSTALL_FOLDER, \
    BRING_PKG_DATA_FOLDER_NAME
from bring.pkg.versions import PkgVersion, get_version_sources_factory, VersionSource
from bring.transform.pipeline import Pipeline
from bring.transform.transformer import explode_transform_value
from bring.transform.transformers.folder_content import convert_content_spec_items
from frkl.args.hive import ArgHive
from frkl.common.async_utils import wrap_async_task
from frkl.common.dicts import get_seeded_dict
from frkl.common.doc import Doc
from frkl.common.exceptions import FrklException
from frkl.common.filesystem import ensure_folder
from frkl.targets.target import Target
from frkl.types.plugins import PluginFactory
from tings.tingistry import Tingistry


def calculate_package_id(pkg: "Pkg", version: PkgVersion) -> str:

    return f"{version.id}_{pkg.transform_hash}"


class Pkg(metaclass=ABCMeta):
    """Class to hold information about a bring package.

    Information includes:
      - a list of available versions
      - steps to retrieve the package (one list of steps per version)
      - steps to do some pre-install transformation(s)
      - metadata (license, author, homepage, description, ...)
      - tags
      - labels

    Args:

        pkg (Mapping): data necessary to create the list of package versions
        vars (Mapping): TODO
        aliases (Mapping): a map of value aliases used to translate parameters
        args (Mapping): a map of required or optional arguments that can be set to select a version, and/or control the install process
        tags (Iterable): a list of tags for this package
        labels (Mapping): a map of labels for this package
        transform (Any): configuration for the pre-install transformation (applies to all versions -- check 'explode_transform_value' for details on allowed input)
    """


    def __init__(self, tingistry: Tingistry, pkg: Mapping[str, Any], vars: Optional[Mapping[str, Any]]=None, aliases: Optional[Mapping[str, Mapping[Any, Any]]]=None, args: Optional[Mapping[str, Any]]=None, info: Union[str, Mapping[str, Any], None]=None, tags: Optional[Iterable[str]]=None, labels: Optional[Mapping[str, Any]]=None, transform: Any=None, content: Any=None):

        self._tingistry: Tingistry = tingistry
        self._pkg_data: Mapping[str, Any] = pkg
        if vars is None:
            vars = {}
        self._vars: Mapping[str, Any] = vars
        if aliases is None:
            aliases = {}
        self._pkg_aliases: Mapping[str, Mapping[Any, Any]] = aliases
        self._aliases: Optional[Mapping[str, Mapping[Any, Any]]] = None
        if args is None:
            args = {}
        self._args: Mapping[str, Any] = args
        if info is None:
            self._info = Doc(short_help_key="slug", help_key="desc")
        else:
            self._info: Doc = Doc(info, short_help_key="slug", help_key="desc")
        if tags is None:
            tags = []
        self._tags: Iterable[str] = tags
        self._labels: Mapping[str, Any] = labels

        self._transform: List[Mapping[str, Any]] = explode_transform_value(transform)
        if content:
            content_spec = convert_content_spec_items(content)
            content_transformer = {
                "type": "folder_content",
                "content_spec": content_spec
            }
            self._transform.append(content_transformer)

        self._transform_hash: Optional[str] = None


    @property
    def tingistry(self) -> Tingistry:
        return self._tingistry

    @property
    def pkg_data(self) -> Mapping[str, Any]:
        return self._pkg_data

    @property
    def vars(self) -> Mapping[str, Any]:
        return self._vars

    @property
    def args(self) -> Mapping[str, Any]:
        return self._args

    @property
    def info(self) -> Mapping[str, Any]:
        return self._info

    @property
    def tags(self) -> Iterable[str]:
        return self._tags

    @property
    def labels(self) -> Mapping[str, Any]:
        return self._labels

    @property
    def transform(self) -> Sequence[Mapping[str, Any]]:
        return self._transform

    @property
    def transform_hash(self) -> str:

        if self._transform_hash is None:
            hashes = DeepHash(self.transform)
            self._transform_hash = str(hashes[self.transform])
        return self._transform_hash

    @abstractmethod
    async def get_versions(self) -> Iterable[PkgVersion]:
        """Retrieve version objects for this package.

        """
        pass

    def to_dict(self) -> Dict[str, Any]:

        result = {}
        result["pkg"] = self.pkg_data
        result["vars"] = self.vars
        result["args"] = self.args
        result["info"] = self.info.to_dict()
        result["tags"] = self.tags
        result["labels"] = self.labels
        result["transform"] = self.transform
        result["transform_hash"] = self.transform_hash
        result["pkg_versions"] = [x.to_dict() for x in self.pkg_versions]

        return result


class ResolvePkg(Pkg):
    """Pkg implementation that uses a plugin-system to retrieve version data for a package.

    The base plugin class that is used is 'VersionSource'. To implement a specific type of metadata source for versions
    of a package, create a class that inherits from it.

    TODO
    """

    def __init__(self, tingistry: Tingistry, pkg: Mapping[str, Any], vars: Optional[Mapping[str, Any]]=None, aliases: Optional[Mapping[str, Mapping[Any, Any]]]=None, args: Optional[Mapping[str, Any]]=None, info: Union[str, Mapping[str, Any], None]=None, tags: Optional[Iterable[str]]=None, labels: Optional[Mapping[str, Any]]=None, transform: Any=None, content: Any=None):

        self._version_source: Optional[VersionSource] = None

        super().__init__(tingistry=tingistry, pkg=pkg, vars=vars, aliases=aliases, args=args, info=info, tags=tags, labels=labels, transform=transform, content=content)

    @property
    def version_source(self) -> VersionSource:

        if self._version_source is None:

            pkg_data = dict(self.pkg_data)
            pkg_type = pkg_data.pop("type")

            version_sources_factory: PluginFactory = get_version_sources_factory(self._tingistry.arg_hive)
            self._version_source = version_sources_factory.create_plugin(pkg_type, tingistry=self._tingistry, **pkg_data)

        return self._version_source

    async def get_versions(self) -> Iterable[PkgVersion]:

        return  await self.version_source.get_versions()

    async def install(self, **input_values: Any) -> str:

        version = await self.version_source.find_matching_version(**input_values)

        package_base_path = self.version_source.calculate_version_folder_base_path(version, version_base_dir=BRING_PKG_INSTALL_FOLDER)

        package_cache_path = os.path.join(package_base_path, self.transform_hash, BRING_PKG_DATA_FOLDER_NAME)
        package_metadata_file = os.path.join(package_base_path, self.transform_hash, f"{self.transform_hash}.json")

        if not os.path.exists(package_cache_path):

            # create the version folder if necessary, then create a disposable copy
            version_folder = await self.version_source.get_version_folder(version, read_only=False)
            def delete_version_folder():
                shutil.rmtree(version_folder, ignore_errors=True)
            atexit.register(delete_version_folder)

            pipeline = Pipeline(tingistry=self.tingistry, task_name="install_pkg")
            pipeline.add(self._transform)
            pipeline.set_input(folder_path=version_folder)

            pipeline_result = await pipeline.run_async(raise_exception=True)

            folder_path = pipeline_result.result_value["folder_path"]

            ensure_folder(os.path.dirname(package_cache_path))

            # TODO: write metadata
            shutil.move(folder_path, package_cache_path)

        return package_cache_path




