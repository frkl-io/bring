# -*- coding: utf-8 -*-
import collections
import copy
import os
import shutil
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, Optional, Union, Dict, List

from bring.transform.transformer import SimpleTransformer
from frkl.common.exceptions import FrklException
from frkl.common.filesystem import ensure_folder
from frkl.common.types import isinstance_or_subclass
from frkl.targets.local_folder import LocalFolder, log
from frkl.targets.target import MetadataFileItem, TargetItem


# from bring.merge_strategy import FolderMerge, MergeStrategy
PKG_SPEC_DEFAULTS = {"flatten": False, "single_file": False}

PATH_KEY = "path"
FROM_KEY = "from"
MODE_KEY = "mode"

ALLOWED_KEYS = [FROM_KEY, PATH_KEY, MODE_KEY]


def convert_content_spec_item(
    from_name: Optional[str] = None, data: Any = None
) -> Dict[str, Any]:

    if data is None:
        return {FROM_KEY: from_name, PATH_KEY: from_name}
    elif isinstance(data, str):
        return {FROM_KEY: from_name, PATH_KEY: data}
    elif isinstance(data, collections.abc.Mapping):

        if from_name and FROM_KEY in data.keys():
            if from_name != data[FROM_KEY]:
                raise FrklException(
                    msg=f"Can't parse transform item: {from_name}/{data}.",
                    reason=f"Duplicate, non-equal '{FROM_KEY}' keys.",
                )

        result: Dict[str, Any] = dict(data)
        if from_name:
            result[FROM_KEY] = from_name
        if PATH_KEY not in data.keys():
            result[PATH_KEY] = from_name

        for k, v in data.items():
            if k not in ALLOWED_KEYS:
                raise FrklException(
                    msg=f"Can't parse transform item: {data}.",
                    reason=f"Invalid key: {k}",
                )

        return result
    else:
        raise FrklException(
            msg=f"Can't parse transform item: {data}",
            reason=f"Invalid type: {type(data)}",
        )


def convert_content_spec_items(items: Any) -> List[Dict[str, Any]]:

    if not items:
        _items: List[Dict[str, Any]] = []
    elif isinstance(items, str):
        _items = [convert_content_spec_item(items)]
    elif isinstance(items, collections.abc.Mapping):
        _items = []

        all_allowed_items = True
        for k, v in items.items():
            if k not in ALLOWED_KEYS:
                all_allowed_items = False
                break
        if all_allowed_items:
            item = convert_content_spec_item(data=items)
            _items.append(item)
        else:
            for from_name, data in items.items():
                item = convert_content_spec_item(from_name=from_name, data=data)
                _items.append(item)
    elif isinstance(items, collections.abc.Iterable):
        _items = []
        for item in items:
            if isinstance(item, str):
                item = convert_content_spec_item(item)
                _items.append(item)
            elif isinstance(item, collections.abc.Mapping):
                first_key = next(iter(item))
                if len(item) == 1 and first_key != FROM_KEY:
                    item = convert_content_spec_item(
                        from_name=first_key, data=item[first_key]
                    )
                else:
                    item = convert_content_spec_item(data=item)
                _items.append(item)
            else:
                raise FrklException(
                    f"Can't parse transform item: {item}",
                    reason=f"Invalid type: {type(item)}",
                )
    else:
        raise FrklException(
            f"Can't parse transform item: {items}",
            reason=f"Invalid type: {type(items)}",
        )

    return _items


class ContentSpec(object):
    @classmethod
    def create(cls, pkg_spec: Any) -> "PkgSpec":

        if isinstance_or_subclass(pkg_spec, ContentSpec):
            return pkg_spec

        pkg_spec_obj = ContentSpec(pkg_spec)
        return pkg_spec_obj

    def __init__(
        self, data: Any = None,
    ):

        self._items: Dict[str, Mapping[str, Any]] = {}
        item_list = convert_content_spec_items(data)

        for item in item_list:
            path = item[PATH_KEY]
            if path in self._items.keys():
                raise FrklException(
                    f"Can't use transform items: {data}",
                    reason=f"Duplicate target path: {path}",
                )
            self._items[path] = item

    @property
    def pkg_items(self) -> Mapping[str, Mapping[str, Any]]:
        return self._items

    def get_source_item_details(self, item: str) -> List[Mapping[str, Any]]:

        if not self._items:
            return [{PATH_KEY: item, FROM_KEY: item}]

        result = []

        for v in self._items.values():
            if v[FROM_KEY] == item:
                result.append(v)

        return result

    def get_target_item_details(self, item: str) -> Optional[Mapping[str, Any]]:

        if not self._items:
            return {PATH_KEY: item, FROM_KEY: item}

        return self._items.get(item, None)

    def to_dict(self) -> Dict[str, Any]:

        result: Dict[str, Any] = {}
        result["items"] = copy.deepcopy(self.pkg_items)
        return result


class PkgContentLocalFolder(LocalFolder):
    def __init__(self, path: Union[str, Path], content_spec: Any):

        self._content_spec_raw = content_spec
        self._content_spec: ContentSpec = ContentSpec.create(self._content_spec_raw)

        self._merged_items: MutableMapping[str, TargetItem] = {}

        super().__init__(path=path)

    @property
    def content_spec(self) -> ContentSpec:

        return self._content_spec

    async def _merge_item(
        self,
        item_id: str,
        item: Any,
        item_metadata: Mapping[str, Any],
        merge_config: Mapping[str, Any],
    ) -> Optional[MutableMapping[str, Any]]:

        item_matches = self.content_spec.get_source_item_details(item_id)

        for item_details in item_matches:
            if not item_details:

                log.debug(f"Ignoring file item: {item_id}")
                return None

            target_id = item_details[PATH_KEY]
            target_path = os.path.join(self.path, target_id)

            # if self.pkg_spec.single_file:
            #     childs = os.listdir(self.path)
            #     if childs:
            #         raise FrklException(
            #             msg=f"Can't merge item '{item_id}'.",
            #             reason=f"Package is marked as single file, and target path '{self.path}' already contains a child.",
            #         )

            ensure_folder(os.path.dirname(target_path))

            move_method = merge_config.get("move_method", "copy")
            if move_method == "move":
                shutil.move(item, target_path)
            elif move_method == "copy":
                shutil.copy2(item, target_path)
            else:
                raise ValueError(f"Invalid 'move_method' value: {move_method}")

            if "mode" in item_details.keys():
                mode_value = item_details["mode"]
                if not isinstance(mode_value, str):
                    mode_value = str(mode_value)

                mode = int(mode_value, base=8)
                os.chmod(target_path, mode)

            self._merged_items[target_path] = MetadataFileItem(
                id=target_path, parent=self, metadata=item_metadata
            )

        return {"msg": "installed"}

    async def _get_items(self, *item_ids: str) -> Mapping[str, Optional[TargetItem]]:

        return self._merged_items

    async def _get_managed_item_ids(self) -> Iterable[str]:

        return self._merged_items.keys()


class FolderContent(SimpleTransformer):
    """Merge multiple folders into a single one, using one of the available merge strategies.

    This mogrifier is used internally, and, for now, can't be used in user-created mogrifier lists.
    """

    _plugin_name: str = "folder_content"

    _requires: Mapping[str, str] = {
        "folder_path": "list",
        "files": "list?",
        # "pkg_vars": "dict?",
        "content_spec": "any?",
    }

    _provides: Mapping[str, str] = {"folder_path": "string"}

    def get_msg(self) -> str:

        return "validating package content"

    async def retrieve(self, *value_names: str, **requirements) -> Mapping[str, Any]:

        target_path = self.create_temp_dir("pkg_")
        folder_path = requirements["folder_path"]

        content_spec = requirements.get("content_spec", None)
        # pkg_vars = requirements["pkg_vars"]
        pkg_vars = {}

        folder = PkgContentLocalFolder(path=target_path, content_spec=content_spec)

        await folder.merge_folders(folder_path, item_metadata=pkg_vars)

        return {"folder_path": target_path, "target": folder}
