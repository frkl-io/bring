# -*- coding: utf-8 -*-
import os
from typing import Any, List, Mapping, Optional

from bring.bring import Bring
from bring.bringins import BringIns
from bring.defaults import BRING_TEMP_FOLDER_MARKER
from bring.pkg_index import PkgTing
from bring.utils.pkgs import PkgVersionExplanation
from frtls.async_helpers import wrap_async_task
from rich import box
from rich.console import Console, ConsoleOptions, RenderGroup, RenderResult
from rich.panel import Panel


class BringInsExplanation(object):
    def __init__(
        self,
        bring: Bring,
        bring_ins: BringIns,
        target: Optional[str] = None,
        **vars: Any,
    ):

        self._bring: Bring = bring
        self._bring_ins: BringIns = bring_ins
        if target is None:
            target = BRING_TEMP_FOLDER_MARKER
        self._target: str = target
        self._vars: Mapping[str, Any] = vars
        self._strategy = "default"

        self._explanations: Optional[List[PkgVersionExplanation]] = None

    async def get_pkg_explanations(self):

        if self._explanations is not None:
            return self._explanations

        self._explanations = []
        for item in self._bring_ins.childs:

            _vars = item.process_vars(self._vars)
            _mogrify = item.process_mogrify(self._vars)

            pkg: PkgTing = await item.get_pkg(self._bring)
            expl = PkgVersionExplanation(
                pkg,
                target=BRING_TEMP_FOLDER_MARKER,
                extra_mogrifiers=_mogrify,
                _box_style=box.SIMPLE,
                **_vars,
            )
            self._explanations.append(expl)

        return self._explanations

    def __console__(self, console: Console, options: ConsoleOptions) -> RenderResult:

        explanations = wrap_async_task(self.get_pkg_explanations)
        pkg_panels = []
        for expl in explanations:
            group = RenderGroup(
                f" [title]Package[/title]: [bold dark_red]{expl._pkg.bring_index.name}[/bold dark_red].[bold blue]{expl._pkg.name}[/bold blue]",
                expl,
            )
            pkg_panels.append(Panel(group))

        all: List[Any] = []
        all.append(
            f"[title]Bring manifest[/title]: [bold]{self._bring_ins.id}[/bold]\n\n[title]Tasks[/title]\n\n[title]⮞ install packages into temporary folders[/title]"
        )
        all.extend(pkg_panels)

        if self._target == BRING_TEMP_FOLDER_MARKER:
            target = "<temporary folder>"
        else:
            target = os.path.abspath(self._target)
        all.append(
            f"[title]⮞ merge temporary folders into: {target} (strategy: {self._strategy})[/title]"
        )
        yield Panel(RenderGroup(*all))