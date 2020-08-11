# -*- coding: utf-8 -*-
from typing import TYPE_CHECKING, Any, Mapping, Union

from bring.frecklets import BringFrecklet
from frkl.args.arg import Arg


if TYPE_CHECKING:
    from freckles.core.frecklet import FreckletVar


class BringTemplateFrecklet(BringFrecklet):
    async def get_base_args(self) -> Mapping[str, Union[str, Arg, Mapping[str, Any]]]:

        return {
            "templates_pkg": {
                "type": "string",
                "required": True,
                "doc": "a list of packages to install",
                "default": "collections.templates",
            },
            "template": {
                "type": "string",
                "required": True,
                "doc": "the name of the template to render",
            },
            "target": {"type": "string", "doc": "the target folder", "required": False},
            "target_config": {
                "type": "dict",
                "doc": "(optional) target configuration",
                # TODO: reference
                "required": False,
            },
        }

    async def input_received(self, **input_vars: "FreckletVar") -> Any:

        if self.current_amount_of_inputs == 0:
            return None

        # data = input_vars["data"].value
        # bring_assembly = await BringAssembly.create_from_string(self._bring, data)
        #
        # self.set_processed_input("assembly", bring_assembly)
        #
        # args = await bring_assembly.get_required_args()
        #
        # return self._bring.arg_hive.create_record_arg(childs=args)


#
#     async def get_required_args(
#         self, **base_vars: Any
#     ) -> Optional[Mapping[str, Union[str, Arg, Mapping[str, Any]]]]:
#
#         template = await self.get_template(**base_vars)
#
#         args = await template.get_value("args")
#         return args
#
#     async def get_template(self, **input_vars: Any) -> TemplaTing:
#
#         templates_pkg = input_vars["templates_pkg"]
#         template_name = input_vars["template"]
#         pkg: Optional[PkgTing] = await self._bring.get_pkg(templates_pkg)
#
#         if pkg is None:
#             raise FrklException(
#                 msg=f"Can't retrieve args for pkg '{templates_pkg}'.",
#                 reason="Package with that name does not exist.",
#             )
#
#         result = await pkg.get_version_folder(input_vars=input_vars)
#         path = result["path"]
#         version_hash = result["version_hash"]
#
#         tempting_repo: TemplaTingRepo = self._bring.tingistry.create_singleting(  # type: ignore
#             f"{self.full_name}.plugins.template.{version_hash}", TemplaTingRepo
#         )
#         if tempting_repo is None:
#             raise Exception("tempting repo not set, this is a bug")
#         tempting_repo.add_repo_path(path)
#
#         temptings: Mapping[str, TemplaTing] = await tempting_repo.get_temptings()
#
#         if template_name not in temptings.keys():
#             raise FrklException(
#                 msg=f"Can't retrieve template '{template_name}' from template package '{templates_pkg}.'",
#                 reason=f"No template with that name included, available templates: '{', '.join(temptings.keys())}'",
#             )
#
#         template: Optional[TemplaTing] = temptings.get(template_name)
#         if template is None:
#             raise FrklException(
#                 msg=f"Can't retrive template '{template_name}'.",
#                 reason="No such template.",
#             )
#
#         return template
#
#     async def create_processing_tasks(
#         self, **input_vars: Any
#     ) -> Union[Task, Iterable[Task], "Frecklet", Iterable["Frecklet"]]:
#
#         pass
