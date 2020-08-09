# -*- coding: utf-8 -*-
from collections import OrderedDict
from typing import Any, Dict, Mapping, MutableMapping, Optional

import git
from bring.pkg_types import PkgType, PkgVersion
from bring.utils.git import ensure_repo_cloned
from pydriller import Commit, GitRepository


class GitRepo(PkgType):
    """A package that represents a git repository and its content.

    The only argument required is the git repository url. *bring* will download and cache (unless otherwise configured) the whole repo.

    Depending on the repository size this might or might not be desirable. If the repository is large, and only one or a few files are wanted, it is probably better to use the ``git_files`` (or ``github_files``, ``gitlab_files``, ...) package type, as this only downloads the files needed. If one git repository is the shared source for multiple packages, this package type might be the better choice though, since it will be only downloaded and cached once, and retrieval of each of those packages is quicker (since the git repository is cached locally, and only a ``git checkout`` is necessary to retrieve a specific version).

    By default, all tags and branches will be used as version names. If '*use_commits_as_versions*' is set to '*true*',
    also the commit hashes will be used. An alias '*latest*' will be added, pointing to the latest tag, or, in case no
    tags exist, to the 'master' branch.

    Examples:
      - scripts.bashtop
    """

    _plugin_name: str = "git_repo"
    _plugin_supports: str = "git_repo"

    def __init__(self, **config: Any):

        super().__init__(**config)

    # def _name(self):
    #
    #     return "git"

    def get_args(self) -> Mapping[str, Any]:

        return {
            "url": {"type": "string", "required": True, "doc": "The git repo url."},
            "use_commits_as_versions": {
                "type": "boolean",
                "required": False,
                "default": False,
                "doc": "Whether to use commit hashes as version strings.",
            },
        }

    def _get_unique_source_type_id(self, source_details: Mapping) -> str:

        return source_details["url"]

    async def _process_pkg_versions(self, source_details: Mapping) -> Mapping[str, Any]:

        cache_path = await ensure_repo_cloned(url=source_details["url"], update=True)

        gr = GitRepository(cache_path)
        commits: MutableMapping[str, Commit] = OrderedDict()
        tags: MutableMapping[str, git.objects.commit.Commit] = OrderedDict()
        branches: MutableMapping[str, git.objects.commit.Commit] = OrderedDict()

        for c in gr.get_list_commits():
            commits[c.hash] = c

        for t in reversed(
            sorted(gr.repo.tags, key=lambda t: t.commit.committed_datetime)
        ):
            tags[t.name] = t.commit

        for b in gr.repo.branches:
            branches[b.name] = b.commit

        versions = []

        latest: Optional[str] = None
        for k in tags.keys():

            if latest is None:
                latest = k

            if tags[k].hexsha not in commits.keys():
                await self._update_commits(gr, commits, k)
            c = commits[tags[k].hexsha]
            timestamp = str(c.author_date)
            _v = PkgVersion(
                steps=[
                    {"type": "git_clone", "url": source_details["url"], "version": k}
                ],
                vars={"version": k},
                metadata={"release_data": timestamp},
            )
            versions.append(_v)

        if "master" in branches.keys():
            if latest is None:
                latest = "master"
            c = commits[branches["master"].hexsha]
            timestamp = str(c.author_date)
            _v = PkgVersion(
                steps=[
                    {
                        "type": "git_clone",
                        "url": source_details["url"],
                        "version": "master",
                    }
                ],
                vars={"version": "master"},
                metadata={"release_data": timestamp},
            )
            versions.append(_v)

        for b in branches.keys():
            if b == "master":
                continue

            if branches[b].hexsha not in commits.keys():
                await self._update_commits(gr, commits, b)
            c = commits[branches[b].hexsha]
            timestamp = str(c.author_date)

            _v = PkgVersion(
                steps=[
                    {"type": "git_clone", "url": source_details["url"], "version": b}
                ],
                vars={"version": b},
                metadata={"release_data": timestamp},
            )
            versions.append(_v)

        if source_details.get("use_commits_as_versions", False):
            for c_hash, c in commits.items():
                timestamp = str(c.author_date)

                _v = PkgVersion(
                    steps=[
                        {
                            "type": "git_clone",
                            "url": source_details["url"],
                            "version": c_hash,
                        }
                    ],
                    vars={"version": c_hash},
                    metadata={"release_data": timestamp},
                )
                versions.append(_v)

        result: Dict[str, Any] = {"versions": versions}

        if latest is not None:
            aliases: Dict[str, Any] = {"version": {}}
            aliases["version"]["latest"] = latest
            result["aliases"] = aliases

        return result

    async def _update_commits(
        self,
        git_repo: GitRepository,
        current_commits: MutableMapping,
        checkout_point: str,
    ) -> None:

        for c in git_repo.get_list_commits(rev=checkout_point):
            if c.hash not in current_commits.keys():
                current_commits[c.hash] = c
