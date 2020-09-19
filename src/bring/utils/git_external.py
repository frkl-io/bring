# -*- coding: utf-8 -*-
import os
import shutil
from typing import Mapping, Dict, Any

from pydriller import GitRepository

from bring.defaults import BRING_GIT_CHECKOUT_CACHE
from frkl.common.downloads.cache import calculate_cache_path
from frkl.common.filesystem import ensure_folder
from frkl.common.strings import generate_valid_identifier
from frkl.common.subprocesses import GitProcess


async def ensure_repo_cloned(url, update=False) -> str:

    path = calculate_cache_path(base_path=BRING_GIT_CHECKOUT_CACHE, url=url)
    parent_folder = os.path.dirname(path)

    exists = False
    if os.path.exists(path):
        exists = True

    if exists and not update:
        return path

    ensure_folder(parent_folder)

    if not exists:
        # clone to a temp location first, in case another process tries to do the same
        temp_name = generate_valid_identifier()
        temp_path = os.path.join(parent_folder, temp_name)
        git = GitProcess(
            "clone", url, temp_path, working_dir=parent_folder, GIT_TERMINAL_PROMPT="0"
        )

        await git.run(wait=True)

        if os.path.exists(path):
            shutil.rmtree(temp_path, ignore_errors=True)
        else:
            shutil.move(temp_path, path)

    else:
        # TODO: some sort of lock?
        git = GitProcess("fetch", working_dir=path)

        await git.run(wait=True)

    return path

def get_repo_info(local_path: str) -> Mapping[str, Mapping[str, Any]]:

    gr = GitRepository(local_path)

    commits = get_commits_info(gr)
    tags = get_tags_from_repo(gr)
    branches = get_branches_from_repo(gr)

    result = {
        "branches": branches,
        "tags": tags,
        "commits": commits
    }

    return result


def get_commits_info(gr: GitRepository) -> Mapping[str, Mapping[str, Any]]:

    commits: Dict[str, Mapping[str, Any]] = {}
    for c in gr.get_list_commits():
        commits[c.hash] = {
            "author_date": c.author_date,
            "author_timezone": c.author_timezone
        }
    return commits

def get_branches_from_repo(gr: GitRepository) -> Mapping[str, str]:
    """Retrieve all branches from provided git repo.

    Returns:
        Mapping: a dict with the branch name as key, and the commit hash of its head as value
    """

    branches: Dict[str, str] = {}
    for b in gr.repo.branches:
        branches[b.name] = b.commit.hexsha

    return branches


def get_tags_from_repo(gr: GitRepository) -> Mapping[str, str]:
    """Retrieve all tags from provided git repo.

    Returns:
        Mapping: a dict with the tag name as key, and the commit hash it refers to as value
    """

    tags: Dict[str, str] = {}
    for t in reversed(
            sorted(gr.repo.tags, key=lambda t: t.commit.committed_datetime)
        ):
        tags[t.name] = t.commit.hexsha

    return tags
