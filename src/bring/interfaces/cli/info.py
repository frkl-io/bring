# -*- coding: utf-8 -*-
import arrow
import asyncclick as click
from bring.bring import Bring
from bring.context import BringContextTing
from frtls.cli.exceptions import handle_exc_async
from frtls.cli.group import FrklBaseCommand
from frtls.formats.output import serialize
from prompt_toolkit import HTML, print_formatted_text as print


class BringInfoGroup(FrklBaseCommand):
    def __init__(
        self,
        bring: Bring,
        context: str = None,
        name=None,
        print_version_callback=None,
        no_args_is_help=None,
        chain=False,
        result_callback=None,
        callback=None,
        **kwargs,
    ):

        self.print_version_callback = print_version_callback
        # self.params[:0] = self.get_common_options(
        #     print_version_callback=self.print_version_callback
        # )
        self._bring: Bring = bring
        if context:
            _context = self._bring.get_context(context)
        else:
            _context = None
        self._context: BringContextTing = _context

        super(BringInfoGroup, self).__init__(
            name=name,
            invoke_without_command=True,
            no_args_is_help=False,
            chain=False,
            result_callback=None,
            callback=self.all_info,
            arg_hive=bring.arg_hive,
            **kwargs,
        )

    async def init_command_async(self, ctx):

        await self._bring.init()

    @click.pass_context
    async def all_info(ctx, self, *args, **kwargs):

        if ctx.invoked_subcommand:
            return

        if not self._context:
            return await self.all_info_no_context()

        print()
        print(HTML("<b>Available packages:</b>"))
        print()
        pkgs = await self._context.pkgs

        if not pkgs.pkgs:
            print("  - no packages")
        for pkg in pkgs:
            print(HTML(f"  - {pkg.name}"))
        print()

    async def all_info_no_context(self):

        print()
        print(HTML("<b>Available contexts:</b>"))
        print()
        for context in self._bring.contexts.values():
            print(HTML(f"<slategray><b>{context.name}</b></slategray>"))
            print()
            print(HTML("  Packages:"))
            print()
            pkgs = await context.pkgs
            if not pkgs.pkgs:
                print("    - no packages")
            for pkg in pkgs:
                print(HTML(f"    - {pkg.name}"))
            print()

    async def _list_commands(self, ctx):

        if self._context is not None:
            pkg_names = await self._context.pkg_names
            return sorted(pkg_names)

        all = []
        for context in self._bring.contexts.values():
            pkg_names = await context.pkg_names
            all.extend([f"{context.name}__{x}" for x in pkg_names])

        return sorted(all)

    async def _get_command(self, ctx, name):

        if self._context is not None:
            pkg = await self._context.get_pkg(name)
        else:
            if "__" not in name:
                return None
            context_name, pkg_name = name.split("__")
            context = self._bring.get_context(context_name)
            pkg = await context.get_pkg(pkg_name)

        @click.command(name=name)
        @click.option("--update", "-u", help="update metadata", is_flag=True)
        @click.option("--full", "-f", help="display full info", is_flag=True)
        @handle_exc_async
        async def command(update: bool, full: bool):

            args = {"include_metadata": True}
            if update:
                args["retrieve_config"] = {"metadata_max_age": 0}
            info = await pkg.get_info(**args)

            metadata = info["metadata"]
            age = arrow.get(metadata["timestamp"])

            to_print = {}
            to_print["info"] = info["info"]
            to_print["labels"] = info["labels"]
            to_print["artefact"] = info["artefact"]
            to_print["metadata snapshot"] = age.humanize()
            to_print["vars"] = {
                "defaults": metadata["defaults"],
                "aliases": metadata["aliases"],
                "values": metadata["allowed_values"],
            }
            if full:
                to_print["version list"] = metadata["version_list"]

            click.echo()
            click.echo(serialize(to_print, format="yaml"))

        vals = await pkg.get_values("info")
        command.short_help = vals["info"].get("slug", "n/a")

        return command
