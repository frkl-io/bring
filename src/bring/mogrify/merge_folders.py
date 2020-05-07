# -*- coding: utf-8 -*-
from typing import Any, Mapping, MutableMapping

from bring.mogrify import SimpleMogrifier
from bring.utils.merging import FolderMerge


class MergeFoldersMogrifier(SimpleMogrifier):
    """Merge multiple folders into a single one, using one of the available merge strategies.

    This mogrifier is used internally, and, for now, can't be used in user-created mogrifier lists.
    """

    _plugin_name: str = "merge_folders"

    _requires: Mapping[str, str] = {"folder_paths": "list", "merge_strategy": "dict?"}

    _provides: Mapping[str, str] = {"folder_path": "string"}

    def get_msg(self) -> str:

        return "merging folder (if multiple source folders)"

    async def mogrify(self, *value_names: str, **requirements) -> Mapping[str, Any]:

        strategy: MutableMapping[str, Any] = requirements.get(
            "merge_strategy", {"type": "default", "move_method": "move"}
        )
        if isinstance(strategy, str):
            strategy = {"type": strategy, "move_method": "move"}

        if "move_method" not in strategy.keys():
            strategy["move_method"] = "move"

        folder_paths = requirements["folder_paths"]
        if not folder_paths:
            raise Exception("Can't merge directories, no folder_paths provided.")

        target_path = self.create_temp_dir("merge_")

        merge_obj = FolderMerge(
            typistry=self._tingistry_obj.typistry,
            target=target_path,
            merge_strategy=strategy,
        )

        merge_obj.merge_folders(*folder_paths)

        return {"folder_path": target_path}
