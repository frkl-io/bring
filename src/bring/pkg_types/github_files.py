# -*- coding: utf-8 -*-
import itertools
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional

from bring.pkg_types import PkgType, PkgVersion
from bring.utils.github import get_list_data_from_github
from deepdiff import DeepHash
from frkl.common.exceptions import FrklException
from frkl.common.formats.serialize import serialize
from frkl.common.regex import find_var_names_in_obj


class GitFiles(PkgType):
    """A package type to retrieve one or several files from aa git repository that is hosted on [GitHub](https://github.com).

    This package type directly downloads the required files from GitHub, without downloading the repository itself first.

    This way of accessing files is advantageous if you only need a few, small files, and the repository itself is on the larger side. If this is not the case, consider using the '*git_repo*' package type.

    File-paths specified in the ``files`` argument can contain template place-holders (like: ``deploy/${provider}/config.json``). If that is the case, you need to provide a list of possible values for each of the included placeholders in the ``template_values`` key (check the example below).

    examples:
      - kubernetes.ingress-nginx
    """

    _plugin_name: str = "github_files"
    _plugin_supports: str = "github_files"

    def __init__(self, **config: Any):

        self._github_username = config.get("github_username", None)
        self._github_token = config.get("github_access_token", None)

        super().__init__(**config)

    def get_args(self) -> Mapping[str, Any]:

        return {
            "user_name": {
                "type": "string",
                "required": True,
                "doc": "The github user name.",
            },
            "repo_name": {
                "type": "string",
                "required": True,
                "doc": "The github repo name.",
            },
            "files": {"type": "list", "doc": "The list of files to retrieve."},
            "tag_filter": {
                "type": "string",
                "required": False,
                "doc": "if provided, is used as regex to select wanted tags",
            },
            "template_values": {
                "type": "dict",
                "required": False,
                "doc": "An (optional) map with the possible template var names in the value for 'files' as keys, and all allowed values for each key as value.",
            },
            # "use_commits_as_versions": {
            #     "type": "boolean",
            #     "required": False,
            #     "default": False,
            #     "doc": "Whether to use commit hashes as version strings.",
            # },
        }

    def _get_unique_source_type_id(self, source_details: Mapping) -> str:

        github_user = source_details.get("user_name")
        repo_name = source_details.get("repo_name")
        files: Iterable[str] = source_details.get("files")  # type: ignore

        files = sorted(files)

        hashes = DeepHash(files)
        hash_str = hashes[files]

        return f"{github_user}_{repo_name}_{hash_str}"

    # def get_artefact_mogrify(
    #     self, source_details: Mapping[str, Any], version: PkgVersion
    # ) -> Union[Mapping, Iterable]:
    #
    #     return {"type": "folder"}

    async def _process_pkg_versions(self, source_details: Mapping) -> Mapping[str, Any]:

        github_user: str = source_details.get("user_name")  # type: ignore
        repo_name: str = source_details.get("repo_name")  # type: ignore
        tag_filter: str = source_details.get("tag_filter", None)  # type: ignore

        use_commits = source_details.get("use_commits_as_versions", False)
        _template_values = source_details.get("template_values", {})

        files = source_details["files"]

        template_value_names = find_var_names_in_obj(files)

        missing = []
        needed_template_values: Dict[str, Any] = {}
        for tvn in template_value_names:
            if tvn not in _template_values.keys():
                missing.append(tvn)
            else:
                needed_template_values[tvn] = _template_values[tvn]
                # TODO: check if value is list?

        if missing:
            example_source = dict(source_details)
            for m in missing:
                example_source.setdefault("template_values", {})[m] = [
                    "example_value_1",
                    "example_value_2",
                    "and_so_on",
                ]

            example_source_str = serialize(example_source, format="yaml", indent=4)
            solution = f"Add the missing values to the 'template_values' key:\n\n{example_source_str}"

            raise FrklException(
                msg="Can't create package versions for github_files type.",
                reason=f"'files' value contains template keys, but values for those are not declared in 'template_values': {', '.join(missing)}",
                solution=solution,
            )

        if use_commits:
            raise NotImplementedError("'use_commits_as_versions' is not supprted yet.")

        request_path = f"/repos/{github_user}/{repo_name}/tags"

        tags = await get_list_data_from_github(
            path=request_path,
            github_username=self._github_username,
            github_token=self._github_token,
        )

        request_path = f"/repos/{github_user}/{repo_name}/branches"
        branches = await get_list_data_from_github(
            path=request_path,
            github_username=self._github_username,
            github_token=self._github_token,
        )

        latest: Optional[str] = None
        versions: List[PkgVersion] = []

        tag_names: List[str] = []
        for tag in tags:
            name = tag["name"]
            if tag_filter:
                if not re.match(tag_filter, name):
                    continue
            tag_names.append(name)

        for tag_name in tag_names:

            if latest is None:
                latest = tag_name

            _v = create_pkg_versions(
                user_name=github_user,
                repo_name=repo_name,
                version=tag_name,
                files=files,
                template_values=needed_template_values,
            )
            versions.extend(_v)

        branch_names: List[str] = []
        for b in branches:
            branch_names.append(b["name"])

        if "master" in branch_names:
            if latest is None:
                latest = "master"

            _v = create_pkg_versions(
                user_name=github_user,
                repo_name=repo_name,
                version="master",
                files=files,
                template_values=needed_template_values,
            )
            versions.extend(_v)

        for branch in branch_names:
            if branch == "master":
                continue
            if latest is None:
                latest = branch

            _v = create_pkg_versions(
                user_name=github_user,
                repo_name=repo_name,
                version=branch,
                files=files,
                template_values=needed_template_values,
            )
            versions.extend(_v)

        result: Dict[str, Any] = {"versions": versions}

        if latest is not None:
            aliases: Dict[str, Any] = {"version": {}}
            aliases["version"]["latest"] = latest
            result["aliases"] = aliases

        return result


def create_pkg_versions(
    user_name: str,
    repo_name: str,
    version: str,
    files: Iterable[str],
    template_values: Mapping[str, Any],
) -> Iterable[PkgVersion]:

    # only one version is available
    if not template_values:
        return [
            create_pkg_version(
                user_name=user_name, repo_name=repo_name, version=version, files=files
            )
        ]

    # we need a matrix of all possible template var combinations
    keys, values = zip(*template_values.items())

    versions = [dict(zip(keys, v)) for v in itertools.product(*values)]

    _pkg_versions: List[PkgVersion] = []

    for _pkg_version in versions:
        _v = create_pkg_version(
            user_name=user_name,
            repo_name=repo_name,
            version=version,
            files=files,
            **_pkg_version,
        )
        _pkg_versions.append(_v)

    return _pkg_versions


def create_pkg_version(
    user_name: str,
    repo_name: str,
    version: str,
    files: Iterable[str],
    **extra_vars: Any,
) -> PkgVersion:

    urls = []
    for f in files:
        dl = {
            "url": f"https://raw.githubusercontent.com/{user_name}/{repo_name}/{version}/{f}",
            "target": f,
        }
        urls.append(dl)

    vars = dict(extra_vars)
    vars["version"] = version
    _v = PkgVersion(
        [{"type": "download_multiple_files", "urls": urls}], vars=vars, metadata={},
    )
    return _v
