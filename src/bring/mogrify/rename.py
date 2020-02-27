# -*- coding: utf-8 -*-
import os
import shutil
from typing import Dict

from bring.mogrify import Mogrifier


class RenameTransformer(Mogrifier):

    _plugin_name: str = "rename"

    def __init__(self, **config):

        super().__init__(**config)

    def get_config_keys(self) -> Dict:

        return {"rename": {}}

    def _transform(self, path: str, transform_config: Dict = None) -> str:

        rename = transform_config["rename"]
        if not rename:
            return path

        for source, target in rename.items():
            full_source = os.path.join(path, source)
            full_target = os.path.join(path, target)
            shutil.move(full_source, full_target)

        return path
