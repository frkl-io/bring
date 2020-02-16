# -*- coding: utf-8 -*-
import os
import shutil
from typing import Any, Dict, List

from frtls.exceptions import FrklException

from bring.artefact_handlers import SimpleArtefactHandler


class ArchiveHandler(SimpleArtefactHandler):

    _plugin_name: str = "archive"

    def __init__(self):

        super().__init__()

    def _supports(self) -> List[str]:

        return ["archive"]

    async def _provide_artefact_folder(
        self, artefact_path: str, artefact_details: Dict[str, Any]
    ):

        tempdir = self.create_temp_dir()

        shutil.unpack_archive(artefact_path, tempdir)

        if "remove_root" in artefact_details.keys():
            remove_root = artefact_details["remove_root"]
        else:
            childs = os.listdir(tempdir)
            if len(childs) == 1 and os.path.isdir(os.path.join(tempdir, childs[0])):
                remove_root = True
            else:
                remove_root = False

        if remove_root:
            childs = os.listdir(tempdir)
            if len(childs) == 0:
                raise FrklException(
                    msg="Can't remove archive subfolder.",
                    reason=f"No root file/folder for extracted archive: {artefact_path}",
                )
            elif len(childs) > 1:
                raise FrklException(
                    msg="Can't remove archive subfolder.",
                    reason=f"More than one root files/folders: {', '.join(childs)}",
                )

            root = os.path.join(tempdir, childs[0])
            if not os.path.isdir(root):
                raise FrklException(
                    msg="Can't remove archive root.",
                    reason=f"Not a folder: {childs[0]}",
                )

        else:
            root = tempdir

        return root
