# -*- coding: utf-8 -*-
import collections
import os
from typing import Any, Dict, Mapping, MutableMapping, Optional, Union

from bring.bring import Bring
from bring.defaults import BRING_RESULTS_FOLDER, BRING_WORKSPACE_FOLDER
from bring.pkg import PkgTing
from bring.pkg_index.index import BringIndexTing
from freckles.core.frecklet import Frecklet, FreckletException, FreckletVar
from frkl.common.filesystem import create_temp_dir
from frkl.common.formats.auto import AutoInput
from frkl.common.formats.serialize import to_value_string
from frkl.common.strings import generate_valid_identifier
from tings.ting import TingMeta


def parse_target_data(
    target: Optional[Union[str]] = None,
    target_config: Optional[Mapping] = None,
    temp_folder_prefix: Optional[str] = None,
):

    if (
        not target
        or target.lower() == TEMP_DIR_MARKER
        or BRING_RESULTS_FOLDER in target
        or BRING_WORKSPACE_FOLDER in target
    ):
        _target_path: str = create_temp_dir(
            prefix=temp_folder_prefix, parent_dir=BRING_RESULTS_FOLDER
        )
        _target_msg: str = "new temporary folder"
        _is_temp: bool = True
    else:
        _target_path = target
        _target_msg = f"folder '{_target_path}'"
        _is_temp = False

    if not isinstance(_target_path, str):
        raise TypeError(f"Invalid type for 'target' value: {type(target)}")

    if target_config is None:
        _target_data: MutableMapping[str, Any] = {}
    else:
        if not isinstance(target_config, collections.abc.Mapping):
            raise TypeError(
                f"Invalid type for target_config value '{type(target_config)}'"
            )
        _target_data = dict(target_config)

    if "write_metadata" not in _target_data.keys():
        if _is_temp:
            _target_data["write_metadata"] = False
        else:
            _target_data["write_metadata"] = True

    if _target_data["write_metadata"] is None:
        if _is_temp:
            _target_data["write_metadata"] = False
        else:
            _target_data["write_metadata"] = True

    return {
        "target_config": _target_data,
        "target_path": _target_path,
        "target_msg": _target_msg,
        "is_temp": _is_temp,
    }


class BringFrecklet(Frecklet):
    def __init__(self, name: str, meta: TingMeta, init_values: Mapping[str, Any]):

        self._bring: Bring = init_values["bring"]
        super().__init__(name=name, meta=meta, init_values=init_values)

    @property
    def bring(self) -> Bring:

        return self._bring  # type: ignore

    async def create_pkg_data(self, pkg_input: Union[str, Mapping]) -> Dict[str, Any]:

        pkg_index: Optional[BringIndexTing] = None
        pkg: Optional[PkgTing] = None
        pkg_metadata: Dict[str, Any] = {}

        if isinstance(pkg_input, str):
            _result = await self._bring.get_pkg_and_index(pkg_input)
            if _result is not None:
                pkg_metadata = {"name": _result[0].name, "index": _result[1].id}  # type: ignore
                pkg = _result[0]
                pkg_index = _result[1]

            else:
                full_path = os.path.abspath(os.path.expanduser(pkg_input))
                ai = AutoInput(full_path)
                content = await ai.get_content_async()
                if "source" in content.keys():
                    ting_name = content.get("info", {}).get("name", None)
                    if ting_name is None:
                        ting_name = generate_valid_identifier(pkg_input)
                    pkg = self.tingistry.create_ting(  # type: ignore
                        "bring.types.dynamic_pkg",
                        ting_name=f"{self.full_name}.{ting_name}",
                    )
                    pkg.set_input(**content)  # type: ignore
                    pkg_metadata = {"source": content["source"]}
        elif isinstance(pkg_input, collections.abc.Mapping):

            if "source" in pkg_input.keys():
                _data = pkg_input["source"]
            elif "type" not in pkg_input:
                # TODO: references
                _r = to_value_string(pkg_input, reindent=4)
                raise FreckletException(
                    frecklet=self,
                    msg="Can't create package from provided input dict.",
                    reason=f"Input data does not contain a 'type' key:\n\n{_r}",
                )
            else:
                _data = pkg_input

            pkg_metadata = {"source": _data}

            ting_name = pkg_input.get("info", {}).get("name", None)

            if ting_name is None:
                ting_name = generate_valid_identifier()
            pkg = self.tingistry.create_ting(  # type: ignore
                "bring.types.dynamic_pkg", ting_name=f"{self.full_name}.{ting_name}"
            )
            pkg.set_input(**pkg_input)  # type: ignore
            # pkg_metadata = {"source": pkg_input["source"]}

        if pkg is None:
            input_str = to_value_string(pkg_input, reindent=4)

            reason = f"Invalid input:\n\n{input_str}"
            raise FreckletException(
                frecklet=self,
                msg="Can't create package from provided input.",
                reason=reason,
                solution="Either provide a valid package name string, a pkg description map, or a path to a file containing one.",
            )

        all_defaults: Dict[str, Dict[str, FreckletVar]] = {}
        defaults: Dict[str, FreckletVar] = {}

        if pkg_index:

            index_defaults = await pkg_index.get_index_defaults()
            # index_defaults = await pkg.bring_index.get_index_defaults()
            index_defaults = {}
            for k, v in index_defaults.items():
                fv = FreckletVar(v, origin="index defaults")
                index_defaults[k] = fv
                defaults[k] = fv
            all_defaults["index"] = index_defaults

        bring_defaults = await self._bring.get_defaults()
        context_defaults: Dict[str, FreckletVar] = {}
        for k, v in bring_defaults.items():
            if k not in defaults.keys():
                fv = FreckletVar(v, origin="context defaults")
                context_defaults[k] = fv
                defaults[k] = fv
        all_defaults["context"] = context_defaults

        pkg_defaults = await pkg.get_pkg_defaults()
        p_defaults: Dict[str, FreckletVar] = {}
        for k, v in pkg_defaults.items():
            if k not in defaults.keys():
                fv = FreckletVar(v, origin="package defaults")
                defaults[k] = fv
                p_defaults[k] = fv
        all_defaults["package"] = p_defaults

        result: Dict[str, Any] = {}
        result["pkg"] = pkg
        result["defaults_map"] = all_defaults
        result["defaults"] = defaults
        result["index"] = pkg_index
        result["pkg_metadata"] = pkg_metadata

        return result


TEMP_DIR_MARKER = "__temp__"
