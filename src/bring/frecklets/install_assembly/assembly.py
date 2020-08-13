# -*- coding: utf-8 -*-
import collections
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Union

from anyio import create_task_group
from bring.bring import Bring
from bring.utils import parse_pkg_string
from frkl.args.arg import Arg
from frkl.common.exceptions import FrklException
from frkl.common.formats import VALUE_TYPE
from frkl.common.formats.auto import AutoInput
from frkl.common.iterables import ensure_iterable
from frkl.common.regex import create_var_regex, find_var_names_in_obj


BRING_IN_DEFAULT_DELIMITER = create_var_regex()


class BringAssembly(object):
    @classmethod
    async def create_from_string(cls, bring: Bring, config: Union[str, Path]):

        inp = AutoInput(config)
        content = await inp.get_content_async()
        value_type = await inp.get_value_type_async()

        if value_type == VALUE_TYPE.mapping:
            pkgs: Iterable = content["pkgs"]
        elif value_type == VALUE_TYPE.iterable:
            pkgs = content
        else:
            raise FrklException(
                msg=f"Can't create BringAssembly from config: {config}",
                reason=f"Invalid value type: {value_type}",
            )

        return BringAssembly(bring, *pkgs)

    def __init__(self, bring: Bring, *pkgs: Union[str, Mapping[str, Any]]):

        self._bring: Bring = bring
        self._pkg_data: List[Mapping[str, Mapping[str, Any]]] = []
        self._pkg_map: Optional[MutableMapping[str, MutableMapping[str, Any]]] = None
        _pkg_data: Iterable[Union[MutableMapping[str, Any], str]] = ensure_iterable(pkgs)  # type: ignore
        for pkg_data in _pkg_data:
            if isinstance(pkg_data, str):
                pkg_name, pkg_index = parse_pkg_string(pkg_data)
                if not pkg_index:
                    raise ValueError(
                        f"Invalid pkg item, no 'index' in package name: {pkg_data}"
                    )
                p = {"name": pkg_name, "index": pkg_index}
                self._pkg_data.append({"pkg": p})
            elif isinstance(pkg_data, collections.abc.Mapping):
                if "pkg" not in pkg_data.keys():
                    raise ValueError(f"Invalid package item, no 'pkg' key: {pkg_data}")
                pkg: Union[str, Mapping[str, Any]] = pkg_data["pkg"]
                if isinstance(pkg, str):
                    pkg_name, pkg_index = parse_pkg_string(pkg)
                    if not pkg_index:
                        raise ValueError(
                            f"Invalid pkg item, no 'index' in package name: {pkg_data}"
                        )
                    pkg = {"name": pkg_name, "index": pkg_index}
                    pkg_data["pkg"] = pkg

                if "name" not in pkg.keys():
                    raise ValueError(f"Invalid pkg item, no 'name' key: {pkg_data}")
                if "index" not in pkg.keys():
                    raise ValueError(f"Invalid pkg item, no 'index' key: {pkg_data}")
                if not pkg_data.get("vars", None):
                    pkg_data["vars"] = {}

                self._pkg_data.append(pkg_data)

        # TODO: validate

    @property
    def pkg_data(self) -> Iterable[Mapping[str, Mapping[str, Any]]]:
        return self._pkg_data

    async def get_pkg_map(self) -> Mapping[str, Any]:

        if self._pkg_map is not None:
            return self._pkg_map

        self._pkg_map = {}

        async def get_pkg(_pkg_data: MutableMapping[str, Any]):

            pkg_name = f"{_pkg_data['pkg']['name']}{_pkg_data['pkg']['index']}"

            _pkg = await self._bring.get_pkg(name=pkg_name)

            self._pkg_map[pkg_name] = {"pkg": _pkg, "config": _pkg_data}  # type: ignore

        async with create_task_group() as tg:
            for pkg_data in self._pkg_data:
                await tg.spawn(get_pkg, pkg_data)

        missing = []
        for id, details in self._pkg_map.items():
            if details["pkg"] is None:
                missing.append(id)
        if missing:
            raise FrklException(
                msg="Can't assemble package list.",
                reason=f"No packages found for: {', '.join(missing)}",
            )

        return self._pkg_map  # type: ignore

    async def get_required_args(
        self,
    ) -> Mapping[str, Union[str, Arg, Mapping[str, Any]]]:

        # TODO: parse file for arg definitions
        args_dict: Dict[str, Union[str, Arg, Mapping[str, Any]]] = {}

        var_names = find_var_names_in_obj(
            self._pkg_data, delimiter=BRING_IN_DEFAULT_DELIMITER
        )

        if not var_names:
            return {}

        result: Dict[str, Union[str, Arg, Mapping[str, Any]]] = {}
        for var_name in var_names:
            if var_name in args_dict.keys():
                result[var_name] = args_dict[var_name]
            else:
                result[var_name] = {
                    "type": "any",
                    "required": True,
                    "doc": f"value for '{var_name}'",
                }

        return result
