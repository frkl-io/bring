import os
import shutil
import logging
import time
from threading import Thread
from typing import Mapping, Any, Dict, Optional

from anyio import run_sync_in_worker_thread
from dulwich import porcelain, index
from dulwich.client import HttpGitClient, LocalGitClient
from dulwich.objects import format_timezone, Tag, Commit
from dulwich.objectspec import parse_commit
from dulwich.porcelain import NoneStream
from dulwich.repo import Repo

from bring.defaults import BRING_GIT_CHECKOUT_CACHE
from frkl.common.downloads.cache import calculate_cache_path
from frkl.common.exceptions import FrklException
from frkl.common.filesystem import ensure_folder
from frkl.common.strings import generate_valid_identifier


log = logging.getLogger("bring")

async def ensure_repo_cloned(url, update=False, use_thread: bool=True) -> str:

    path = calculate_cache_path(base_path=BRING_GIT_CHECKOUT_CACHE, url=url)
    parent_folder = os.path.dirname(path)

    exists = False
    if os.path.exists(path):
        exists = True

    if exists and not update:
        return path

    ensure_folder(parent_folder)

    if not exists:

        def git_clone():

            # clone to a temp location first, in case another process tries to do the same
            temp_name = generate_valid_identifier()
            temp_path = os.path.join(parent_folder, temp_name)

            porcelain.clone(url, temp_path, errstream=NoneStream())

            if os.path.exists(path):
                shutil.rmtree(temp_path, ignore_errors=True)
            else:
                shutil.move(temp_path, path)

        task = git_clone

    else:
        def git_fetch():
            # TODO: some sort of lock?
            porcelain.fetch(path, errstream=NoneStream())
        task = git_fetch

    if not use_thread:
        task()
    else:
        await run_sync_in_worker_thread(task)

    return path


async def clone_local_repo_async(source_repo: str, target_path: str, version: Optional[str]=None) -> None:

    await run_sync_in_worker_thread(clone_local_repo, source_repo, target_path, version)


def clone_local_repo(source_repo: str, target_path: str, version: Optional[str]=None) -> None:

    if os.path.exists(target_path):
        raise FrklException("Can't clone local git repo.", reason=f"Target path already exists: {target_path}")

    try:
        parent_folder = os.path.dirname(target_path)

        temp_name = generate_valid_identifier()
        temp_path = os.path.join(parent_folder, temp_name)

        remote: Repo = porcelain.open_repo(source_repo)
        source_config = remote.get_config()

        # TODO: this is slow, copying the whole repo would be faster,
        # but dulwich does not support the 'checkout' command properly yet,
        # there is a chance of dangling files
        # shutil.copytree(source_repo, temp_path)
        # local: Repo = porcelain.open_repo(temp_path)

        local: Repo = porcelain.clone(source=source_repo, target=temp_path, errstream=NoneStream(), checkout=False)

        remote_refs = LocalGitClient().fetch(source_repo, local)

        encoded_path = source_config.get((b'remote', b'origin'), b'url')

        target_config = local.get_config()
        target_config.set((b'remote', b'origin'), b'url', encoded_path)
        target_config.write_to_path()

        for key, value in remote_refs.items():
            if key != b'refs/remotes/origin/HEAD' and key.decode("ASCII").startswith("refs/remotes/") and key not in local.refs.keys():
                local.refs[key] = value

        local_refs = LocalGitClient().get_refs(temp_path)

        if version is None:
            version = "master"

        tag = None
        branch = None
        # commit = None
        tag_commit_obj = None

        for ref, ref_obj in local_refs.items():

            ref = ref.decode("ASCII")

            if ref == f"refs/tags/{version}":
                tag = ref
                obj = local[ref_obj]
                if isinstance(obj, Commit):
                    tag_commit_obj = obj
                elif isinstance(obj, Tag):
                    tag_commit_obj = local[obj.object[1]]
            elif ref == f"refs/heads/{version}":
                branch = ref
            elif ref.startswith("refs/remotes/") and ref.endswith(f"/{version}"):
                branch_ref = f"refs/heads/{version}"
                local.refs[branch_ref.encode("ASCII")] = ref_obj
                branch = branch_ref

        to_set = b"HEAD"

        if tag is None and branch is None:
            raise NotImplementedError()
        elif tag is not None and branch is None:
            local.reset_index(tag_commit_obj.tree)
            del local.refs[to_set]
            local.refs[to_set] = tag_commit_obj.sha().hexdigest().encode("ASCII")
        elif branch is not None and tag is None:
            branch_ref = branch.encode("ASCII")
            local.reset_index(local[branch_ref].tree)
            local.refs.set_symbolic_ref(to_set, branch_ref)
        else:
            raise NotImplementedError()
    except Exception as e:
        log.debug(f"Can't clone local git repo {source_repo} -> {target_path}", exc_info=True)
        import traceback
        traceback.print_exc()
        raise e

    if os.path.exists(target_path):
        shutil.rmtree(temp_path, ignore_errors=True)
        raise FrklException("Can't clone local git repo.", reason=f"Target repository create during cloning process: {target_path}")
    else:
        shutil.move(temp_path, target_path)


def get_repo_info(local_path: str) -> Mapping[str, Mapping[str, Any]]:

    repo: Repo = Repo(local_path)

    commits: Dict[str, Mapping[str, Any]] = {}
    walker = repo.get_walker(
        max_entries=None, reverse=False)
    for entry in walker:
        commit_hash = entry.commit.id.decode('ASCII')

        time_tuple = time.gmtime(entry.commit.author_time + entry.commit.author_timezone)
        time_str = time.strftime("%a %b %d %Y %H:%M:%S", time_tuple)
        timezone_str = format_timezone(entry.commit.author_timezone).decode('ascii')

        commits[commit_hash] = {
            "author_date": time_str,
            "author_timezone": timezone_str
        }

    tags: Dict[str, str] = {}
    branches: Dict[str, str] = {}

    for ref, ref_obj in sorted(repo.get_refs().items(), reverse=True):

        ref = ref.decode("ASCII")
        # commit_hash = commit_hash.decode("ASCII")

        if ref.startswith("refs/tags/"):

            tag_name = ref.split("/")[-1]
            obj = repo.get_object(ref_obj)
            if isinstance(obj, Tag):
                sha_digest = obj.object[1].decode("ASCII")
            elif isinstance(obj, Commit):
                sha_digest = obj.sha().hexdigest()

            tags[tag_name] = sha_digest

        elif ref.startswith("refs/heads/"):
            branch_name = ref.split("/")[-1]
            obj = repo.get_object(ref_obj)
            if not isinstance(obj, Commit):
                raise NotImplementedError()

            sha_digest = obj.sha().hexdigest()

            branches[branch_name] = sha_digest
            # print(obj)

    result = {
        "tags": tags,
        "branches": branches,
        "commits": commits
    }
    return result

