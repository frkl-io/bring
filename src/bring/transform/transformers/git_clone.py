# -*- coding: utf-8 -*-
import os
import shutil
from typing import Any, Mapping

from bring.transform.transformer import SimpleTransformer
from bring.utils.git_python import ensure_repo_cloned, clone_local_repo_async, clone_local_repo
from frkl.common.subprocesses import GitProcess


class GitClone(SimpleTransformer):

    _plugin_name: str = "git_clone"

    _requires: Mapping[str, str] = {"url": "string", "version": "string"}
    _provides: Mapping[str, str] = {"folder_path": "string"}

    def get_msg(self) -> str:

        vals = self.user_input
        url = vals.get("url", "[dynamic url]")
        version = vals.get("version", None)

        result = f"cloning git repository '{url}'"
        if version is not None:
            result = result + f" (version: {version})"

        return result

    async def retrieve(self, *value_names: str, **requirements) -> Mapping[str, Any]:

        result = {}

        if "folder_path" in value_names:
            url = requirements["url"]
            version = requirements["version"]

            cache_path = await ensure_repo_cloned(url=url, update=False)
            temp_folder = self.create_temp_dir("git_repo")

            repo_name = os.path.basename(url)
            if repo_name.endswith(".git"):
                repo_name = repo_name[0:-4]
            target_folder = os.path.join(temp_folder, repo_name)

            clone_local_repo(cache_path, target_path=target_folder, version=version)

            result["folder_path"] = target_folder

        return result
