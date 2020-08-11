# -*- coding: utf-8 -*-
import collections
import copy
import logging
from typing import Any, Dict, List, Mapping, Optional

from frkl.common.exceptions import FrklException
from frkl.common.types import isinstance_or_subclass


log = logging.getLogger("bring")

PKG_SPEC_DEFAULTS = {"flatten": False, "single_file": False}

PATH_KEY = "path"
FROM_KEY = "from"
MODE_KEY = "mode"

ALLOWED_KEYS = [FROM_KEY, PATH_KEY, MODE_KEY]


def convert_pkg_spec_item(
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


def convert_pkg_spec_items(items: Any) -> List[Dict[str, Any]]:

    if not items:
        _items: List[Dict[str, Any]] = []
    elif isinstance(items, str):
        _items = [convert_pkg_spec_item(items)]
    elif isinstance(items, collections.abc.Mapping):
        _items = []

        all_allowed_items = True
        for k, v in items.items():
            if k not in ALLOWED_KEYS:
                all_allowed_items = False
                break
        if all_allowed_items:
            item = convert_pkg_spec_item(data=items)
            _items.append(item)
        else:
            for from_name, data in items.items():
                item = convert_pkg_spec_item(from_name=from_name, data=data)
                _items.append(item)
    elif isinstance(items, collections.abc.Iterable):
        _items = []
        for item in items:
            if isinstance(item, str):
                item = convert_pkg_spec_item(item)
                _items.append(item)
            elif isinstance(item, collections.abc.Mapping):
                first_key = next(iter(item))
                if len(item) == 1 and first_key != FROM_KEY:
                    item = convert_pkg_spec_item(
                        from_name=first_key, data=item[first_key]
                    )
                else:
                    item = convert_pkg_spec_item(data=item)
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


class PkgSpec(object):
    @classmethod
    def create(cls, pkg_spec: Any) -> "PkgSpec":

        if isinstance_or_subclass(pkg_spec, PkgSpec):
            return pkg_spec

        pkg_spec_obj = PkgSpec(pkg_spec)
        return pkg_spec_obj

    def __init__(
        self, data: Any = None,
    ):

        self._items: Dict[str, Mapping[str, Any]] = {}
        item_list = convert_pkg_spec_items(data)

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
