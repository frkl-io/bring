# -*- coding: utf-8 -*-
import os
import shutil
from typing import Dict, Iterable, Union

from bring.transform import Transformer
from frtls.files import ensure_folder
from pathspec import PathSpec, patterns


class FileFilterTransformer(Transformer):

    _plugin_name: str = "file_filter"

    def __init__(self, **config):

        super().__init__(**config)

    def get_config_keys(self) -> Dict:

        return {}

    def _transform(self, path: str, transform_config: Dict = None) -> str:

        matches = self.find_matches(path, transform_config=transform_config)

        if not matches:
            return None

        result = self.create_temp_dir()
        for m in matches:
            source = os.path.join(path, m)
            target = os.path.join(result, m)
            parent = os.path.dirname(target)
            ensure_folder(parent)
            shutil.move(source, target)

        return result

    def find_matches(
        self,
        path: str,
        include_patterns: Union[str, Iterable[str]],
        output_absolute_paths=False,
    ) -> Iterable:

        if isinstance(include_patterns, str):
            _include_patterns: Iterable[str] = [include_patterns]
        else:
            _include_patterns = include_patterns

        path_spec = PathSpec.from_lines(patterns.GitWildMatchPattern, _include_patterns)

        matches = path_spec.match_tree(path)

        if output_absolute_paths:
            matches = (os.path.join(path, m) for m in matches)

        return matches
