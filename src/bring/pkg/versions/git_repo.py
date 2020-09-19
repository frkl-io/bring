import json
import os
import shutil
import tempfile
from collections import OrderedDict
from datetime import datetime
from typing import Mapping, Any, Iterable, MutableMapping, Optional, Dict, Tuple

import arrow
from anyio import open_file
from dateutil.parser import parser

from bring.defaults import VERSION_ARG, BRING_PKG_VERSION_DATA_FOLDER_NAME, BRING_VERSION_METADATA_FILE_NAME, \
    BRING_RESULTS_FOLDER, BRING_WORKSPACE_FOLDER
from bring.transform.pipeline import Pipeline
from bring.utils.git_python import get_repo_info, ensure_repo_cloned, clone_local_repo_async
import logging
# import git
# from pydriller import GitRepository, Commit
from pydriller import GitRepository
from tzlocal import get_localzone

from bring.pkg.versions import PkgVersion, VersionSource
from frkl.common.filesystem import ensure_folder
from frkl.common.strings import generate_valid_identifier

log = logging.getLogger("bring")


def get_metadata_from_commit(**commit_data: Any):

    timestamp = str(commit_data["author_date"])
    timestamp_tz = commit_data["author_timezone"]

    t = arrow.get(f"{timestamp} {timestamp_tz}", 'ddd MMM DD YYYY HH:mm:ss Z')

    return {
        "release_date": str(t.datetime)
    }


class GitRepoSource(VersionSource):
    """VersionSource that retrieves package versions from git metadata."""

    _plugin_name = "git_repo"

    def get_pkg_args(self) -> Mapping[str, Any]:

        return {
            "url": {"type": "string", "required": True, "doc": "The git repo url."},
            "use_commits_as_versions": {
                "type": "boolean",
                "required": False,
                "default": False,
                "doc": "Whether to use commit hashes as version strings.",
            },
        }

    def _get_unique_source_type_id(self):

        # TODO: this is not 100% secure, there is a small chance some ids could overlap, should be all right though

        return generate_valid_identifier(self.validated_pkg_input_values["url"], sep="_")

    async def _retrieve_pkg_versions(self, **source_input) -> Tuple[Iterable[PkgVersion], Mapping[str, Mapping[str, Any]]]:

        url = source_input["url"]
        use_commits_as_version = source_input.get("use_commits_as_versions", False)

        steps = [{"type": "git_clone", "url": url, "version": "${version}"}]

        tz = get_localzone()
        metadata_timestamp =  tz.localize(datetime.now())
        cache_path = await ensure_repo_cloned(url=url, update=True)

        repo_info = get_repo_info(cache_path)

        commits: Mapping[str, Mapping[str, Any]] = repo_info["commits"]
        tags: Mapping[str, str] = repo_info["tags"]
        branches: Mapping[str, str] = repo_info["branches"]

        versions = []

        latest: Optional[str] = None
        for k in tags.keys():

            aliases = None
            if latest is None:
                latest = k
                aliases = {"version": {"latest": k}}

            _remove = []
            if tags[k] not in commits.keys():
                log.warning(f"Ignoring tag '{k}': can't find commit hash '{tags[k]}'")
                _remove.append(k)
            for r in _remove:
                tags.pop(r)

            c_data = commits[tags[k]]

            _v = PkgVersion(
                steps=steps,
                id_vars={"version": k},
                aliases=aliases,
                metadata=get_metadata_from_commit(**c_data),
                metadata_timestamp=metadata_timestamp
            )
            versions.append(_v)

        _remove = []
        for b, commit_hash in branches.items():
            if commit_hash not in commits.keys():
                log.warning(f"Ignoring branch '{b}': can't find commit hash for head '{commit_hash}'")
                _remove.append(k)

        for r in _remove:
            branches.pop(r)

        if "master" in branches.keys():
            aliases = None
            if latest is None:
                latest = "master"
                aliases = {"version": {"latest": "master"}}
            c_data = commits[branches["master"]]
            _v = PkgVersion(
                steps=steps,
                id_vars={"version": "master"},
                aliases=aliases,
                metadata=get_metadata_from_commit(**c_data),
                metadata_timestamp=metadata_timestamp,
            )
            versions.append(_v)

        for b, commit_hash in branches.items():
            if b == "master":
                continue

            c_data = commits[commit_hash]

            _v = PkgVersion(
                steps=steps,
                id_vars={"version": b},
                metadata=get_metadata_from_commit(**c_data),
                metadata_timestamp=metadata_timestamp
            )
            versions.append(_v)

        if use_commits_as_version:
            for c_hash, c_data in commits.items():

                _v = PkgVersion(
                    steps=steps,
                    id_vars={"version": c_hash},
                    metadata=get_metadata_from_commit(**c_data),
                    metadata_timestamp=metadata_timestamp
                )
                versions.append(_v)

        version_arg = dict(VERSION_ARG)
        if latest:
            version_arg["default"] = latest

        args_dict = {
            "version": version_arg
        }

        return versions, args_dict

    async def get_version_folder(self, version: PkgVersion, read_only: bool = False) -> str:

        git_url = version.steps[0]["url"]
        repo_version = version.steps[0]["version"]

        git_repo_path = await ensure_repo_cloned(git_url, update=False)

        version_base_path = self.calculate_version_folder_base_path(version, version_base_dir=None)

        if not os.path.exists(version_base_path):

            # write metadata
            md_file = os.path.join(version_base_path, BRING_VERSION_METADATA_FILE_NAME)
            tz = get_localzone()
            created = str(tz.localize(datetime.now()))
            md = version.to_dict()
            md["created"] = created
            md["cached_git_repo_path"] = git_repo_path

            ensure_folder(version_base_path)
            async with await open_file(md_file, "w") as f:
                await f.write(json.dumps(md))

            target_base_path = BRING_WORKSPACE_FOLDER
        else:
            target_base_path = BRING_RESULTS_FOLDER

        target_path = os.path.join(target_base_path, BRING_PKG_VERSION_DATA_FOLDER_NAME, version.id)
        ensure_folder(os.path.dirname(target_path))

        if not os.path.exists(target_path):

            await clone_local_repo_async(git_repo_path, target_path, version=repo_version)

        return target_path
