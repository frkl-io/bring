# -*- coding: utf-8 -*-

"""Main module."""
import os
from typing import Any, Dict, Mapping

from bring.context import BringContextTing
from bring.defaults import (
    BRINGISTRY_CONFIG,
    BRING_CONTEXTS_FOLDER,
    BRING_WORKSPACE_FOLDER,
)
from bring.interfaces.tui.task_progress import TerminalRunWatch
from frtls.files import ensure_folder
from frtls.tasks import ParallelTasksAsync
from tings.makers.file import TextFileTingMaker
from tings.tingistry import Tingistry


DEFAULT_TRANSFORM_PROFILES = {
    "executable": [
        {"type": "file_filter", "exclude": ["*~", "~*"]},
        {"type": "set_mode", "config": {"set_executable": True, "set_readable": True}},
    ]
}


class Bring(Tingistry):
    def __init__(self, name: str, meta: Dict[str, Any] = None):

        ensure_folder(BRING_WORKSPACE_FOLDER)

        super().__init__(
            name,
            ting_types=BRINGISTRY_CONFIG["ting_types"],
            tings=BRINGISTRY_CONFIG["tings"],
            modules=BRINGISTRY_CONFIG["modules"],
            classes=BRINGISTRY_CONFIG["classes"],
            meta=meta,
        )

        config = {}
        for k, v in os.environ.items():
            k = k.lower()
            if not k.startswith("bring_"):
                continue
            config[k[6:]] = v

        self._typistry.get_plugin_manager("pkg_resolver", plugin_config=config)

        self._context_maker: TextFileTingMaker = self.create_ting(
            "bring.types.config_file_context_maker", "bring.context_maker"
        )

        self._context_maker.add_base_paths(BRING_CONTEXTS_FOLDER)

        self._initialized = False

    async def init(self):
        if not self._initialized:
            await self._context_maker.sync()

    @property
    def contexts(self) -> Mapping[str, BringContextTing]:

        childs = self.get_ting("bring.contexts").childs
        return {x.split(".")[-1]: ctx for x, ctx in childs.items()}

    def get_context(self, context_name: str) -> BringContextTing:

        return self.contexts.get(context_name)

    async def update(self):

        tasks = ParallelTasksAsync()
        for context in self.contexts.values():
            t = await context._create_update_tasks()
            tasks.add_task(t)

        term_run_watch = TerminalRunWatch()

        await term_run_watch.run_tasks(tasks)

    def install(self, pkgs):
        pass

    # async def get_all_pkgs(self) -> Dict[str, PkgTing]:
    #
    #     result = {}
    #     for context_name, context in self.contexts.items():
    #         pkgs = await context.get_pkgs()
    #         for pkg_name, pkg in pkgs.pkgs.items():
    #             result[f"{context_name}:{pkg_name}"] = pkg
    #
    #     return result
