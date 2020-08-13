# -*- coding: utf-8 -*-

import logging
from typing import TYPE_CHECKING, Any, Dict, Mapping, MutableMapping

from frkl.explain.explanation import Explanation


if TYPE_CHECKING:
    from rich.console import ConsoleOptions, Console, RenderResult

log = logging.getLogger("bring")


class InstallMergeResult(Explanation):
    def __init__(self, **metadata: Any):

        self._metadata: Dict[str, Any] = dict(metadata)
        self._items: Dict[str, MutableMapping[str, Any]] = {}

        super().__init__()

    def add_merge_item(self, id: str, **result_metadata: Any) -> None:

        # TODO: check if already exists?
        self._items[id] = dict(result_metadata)
        if "merged" not in self._items[id].keys():
            self._items[id]["merged"] = True
        if "msg" not in self._items[id].keys():
            self._items[id]["msg"] = "merged"

    def add_merge_result(self, result: "InstallMergeResult") -> None:

        self._items.update(result.merged_items)

    async def create_explanation_data(self) -> Mapping[str, Any]:

        return self.merged_items

    def add_metadata(self, key: str, value: Any) -> None:
        self._metadata[key] = value

    @property
    def merged_items(self):
        return self._items

    @property
    def metadata(self) -> Mapping[str, Any]:
        return self._metadata

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":

        if not self.merged_items:
            yield "- no items merged[/italic]'"
            return

        for id, details in self.merged_items.items():
            yield f"  [key2]{id}[/key2]: [value]{details['msg']}[/value]"

        return
