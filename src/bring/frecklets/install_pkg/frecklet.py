# -*- coding: utf-8 -*-
import logging
from typing import Any, Dict, Mapping

from bring.frecklets import BringFrecklet
from bring.frecklets.install_pkg.tasks import BringInstallTask
from bring.pkg import PkgTing
from freckles.core.frecklet import FreckletVar
from frkl.args.arg import RecordArg
from frkl.tasks.task import Task


log = logging.getLogger("bring")


class BringInstallFrecklet(BringFrecklet):
    def _invalidate(self) -> None:

        self._pkg = None

    def get_required_base_args(self) -> RecordArg:

        args = {
            "pkg": {"type": "any", "doc": "the package name or data", "required": True},
            # "pkg_index": {
            #     "type": "string",
            #     "doc": "the name of the index that contains the package",
            #     "required": False,
            # },
            "target": {"type": "string", "doc": "the target folder", "required": False},
            "target_config": {
                "type": "dict",
                "doc": "(optional) target configuration",
                # TODO: reference
                "required": False,
            },
            "transform": {
                "type": "dict",
                "doc": "(optional) transform instructions for the package folder",
                "required": False,
            },
        }
        return self._bring.arg_hive.create_record_arg(childs=args)

    async def input_received(self, **input_vars: FreckletVar) -> Any:

        if self.current_amount_of_inputs == 0:

            pkg_input = input_vars["pkg"].value

            data = await self.create_pkg_data(pkg_input=pkg_input)

            pkg: PkgTing = data["pkg"]
            pkg_metadata: Dict[str, Any] = data["pkg_metadata"]
            defaults: Dict[str, FreckletVar] = data["defaults"]
            # pkg_index: Optional[BringIndexTing] = data["index"]

            self.set_processed_input("pkg", pkg)
            self.set_processed_input("pkg_metadata", pkg_metadata)

            self._msg = f"installing package '{pkg.name}'"

            # we don't want defaults overwrite inputs in this case
            for k in input_vars.keys():
                if k in defaults.keys() and not k == "pkg":
                    defaults.pop(k)

            pkg_args: RecordArg = await pkg.get_pkg_args()

            return (pkg_args, defaults)

        elif self.current_amount_of_inputs == 1:
            pkg_input = self.get_processed_input("pkg")
            if pkg_input is None:
                raise Exception(
                    "No 'pkg' object saved in processed input, this is a bug."
                )
            pkg_aliases: Mapping[str, Mapping[Any, Any]] = await pkg_input.get_aliases()

            replacements: Dict[str, FreckletVar] = {}
            for k, v in input_vars.items():
                if k not in pkg_aliases.keys():
                    continue

                alias_set = pkg_aliases[k]
                if v.value not in alias_set.keys():
                    continue

                replacment_value = alias_set[v.value]
                new_metadata = dict(v.metadata)
                new_metadata["from_alias"] = v.value
                fv = FreckletVar(replacment_value, **new_metadata)
                replacements[k] = fv
            return (None, replacements)

        else:
            return None

    async def _create_frecklet_task(self, **input_values: Any) -> Task:

        pkg = self.get_processed_input("pkg")
        pkg_metadata = self.get_processed_input("pkg_metadata")

        target = input_values.pop("target", None)
        target_config = input_values.pop("target_config", None)
        transform_pkg = input_values.pop("transform", None)

        input_values.pop("pkg")

        item_metadata: Dict[str, Any] = {
            "install": {"pkg": pkg_metadata, "vars": input_values}
        }

        frecklet_task = BringInstallTask(
            pkg=pkg,
            input_values=input_values,
            item_metadata=item_metadata,
            target=target,
            target_config=target_config,
            transform_pkg=transform_pkg,
        )

        return frecklet_task
