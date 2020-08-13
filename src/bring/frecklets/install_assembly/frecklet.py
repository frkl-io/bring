# -*- coding: utf-8 -*-
from typing import Any, Mapping, Optional, Union

from bring.defaults import BRING_DEFAULT_MAX_PARALLEL_TASKS
from bring.frecklets import BringFrecklet
from bring.frecklets.install_assembly.assembly import BringAssembly
from bring.frecklets.install_assembly.tasks import ParallelAssemblyTask
from freckles.core.frecklet import FreckletVar
from frkl.args.arg import RecordArg
from frkl.tasks.task import Task


class BringInstallAssemblyFrecklet(BringFrecklet):
    def get_required_base_args(
        self,
    ) -> Optional[Union[RecordArg, Mapping[str, Mapping[str, Any]]]]:

        args = {
            "data": {
                "type": "any",
                "doc": "a list of packages, or path to a file containing it",
            },
            "target": {"type": "string", "doc": "the target folder", "required": False},
            "target_config": {
                "type": "dict",
                "doc": "(optional) target configuration",
                # TODO: reference
                "required": False,
            },
        }

        return args  # type: ignore

    def get_msg(self) -> str:

        return "installing package-assembly"

    async def input_received(self, **input_vars: FreckletVar) -> Any:

        if self.current_amount_of_inputs == 1:
            return None

        data = input_vars["data"].value
        bring_assembly = await BringAssembly.create_from_string(self._bring, data)

        self.set_processed_input("assembly", bring_assembly)

        args = await bring_assembly.get_required_args()

        return self._bring.arg_hive.create_record_arg(childs=args)

    async def _create_frecklet_task(self, **input_values: Any) -> Task:

        target = input_values.pop("target", None)
        target_config = input_values.pop("target_config", None)

        assembly: BringAssembly = self.get_processed_input("assembly")

        ft = ParallelAssemblyTask(
            bring=self._bring,
            assembly=assembly,
            target=target,
            target_config=target_config,
            max_parallel_tasks=BRING_DEFAULT_MAX_PARALLEL_TASKS,
        )
        return ft
