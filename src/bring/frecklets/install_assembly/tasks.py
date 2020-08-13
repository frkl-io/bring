# -*- coding: utf-8 -*-
import os
import tempfile
from typing import Any, Dict, List, Mapping, Optional

from bring.bring import Bring
from bring.defaults import BRING_WORKSPACE_FOLDER
from bring.frecklets import parse_target_data
from bring.frecklets.install_assembly.assembly import BringAssembly
from bring.frecklets.install_pkg import InstallMergeResult
from frkl.common.exceptions import FrklException
from frkl.targets.local_folder import FolderMergeResult, TrackingLocalFolder
from frkl.tasks.task import PostprocessTask, Task
from frkl.tasks.task_desc import TaskDesc
from frkl.tasks.tasks import ParallelTasksAsync, Tasks


class InstallAssemblyPostprocessTask(PostprocessTask):
    def __init__(
        self,
        previous_task: Task,
        target: Optional[str] = None,
        target_config: Optional[Mapping[str, Any]] = None,
        subtarget_map: Optional[Mapping[str, Any]] = None,
        **kwargs,
    ):

        self._target: Optional[str] = target
        self._target_config: Optional[Mapping[str, Any]] = target_config
        self._subtarget_map: Optional[Mapping[str, Any]] = subtarget_map
        self._target_details = parse_target_data(
            self._target, self._target_config, temp_folder_prefix="install_pkgs_"
        )

        super().__init__(previous_task=previous_task, **kwargs)

    async def postprocess(self, task: Task) -> Any:

        result = task.result.result_value

        if not task.success:
            if task.result.error is None:
                raise FrklException(
                    f"Unknown error when running task '{task.task_desc.name}'."
                )
            else:
                raise task.result.error

        folders: Dict[str, Mapping[str, Any]] = {}

        _target_path = self._target_details["target_path"]
        # _target_msg = self._target_details["target_msg"]
        _merge_config = self._target_details["target_config"]

        for k, v in result.items():

            folder_path = v.result_value["folder_path"]
            metadata = v.result_value["item_metadata"]

            if not self._subtarget_map or not self._subtarget_map.get(k, None):
                _target = _target_path
            else:
                subtarget = self._subtarget_map[k]
                if not os.path.isabs(subtarget):
                    _target = os.path.join(_target_path, subtarget)
                else:
                    _target = subtarget

            folders[folder_path] = {"metadata": metadata, "target": _target}

        merge_result = InstallMergeResult()

        for source_folder, details in folders.items():
            _item_metadata = details["metadata"]
            _target = details["target"]
            target_folder = TrackingLocalFolder(path=_target)
            _result: FolderMergeResult = await target_folder.merge_folders(
                source_folder, item_metadata=_item_metadata, merge_config=_merge_config
            )
            for k, v in _result.merged_items.items():
                full_path = _result.target.get_full_path(k)
                merge_result.add_merge_item(full_path, **v)

        return {
            "folder_path": _target_path,
            "target": target_folder,
            "merge_result": merge_result,
        }


class ParallelAssemblyTask(Tasks):
    def __init__(
        self,
        bring: Bring,
        assembly: BringAssembly,
        target: Optional[str] = None,
        target_config: Optional[Mapping[str, Any]] = None,
        max_parallel_tasks: Optional[int] = None,
        task_desc: Optional[TaskDesc] = None,
    ):

        self._bring: Bring = bring
        self._assembly: BringAssembly = assembly

        self._target: Optional[str] = target
        self._target_config: Optional[Mapping[str, Any]] = target_config
        self._max_parallel_tasks: Optional[int] = max_parallel_tasks

        if task_desc is None:
            task_desc = TaskDesc(
                name="install pkg assembly", msg="installing package assembly"
            )

        super().__init__(task_desc=task_desc)

    async def initialize_tasklets(self) -> None:

        self._tasklets: List[Task] = []

        task_desc = TaskDesc(
            name="retrieve pkgs", msg="retrieve package files in parallel"
        )

        install_tasks = ParallelTasksAsync(
            task_desc=task_desc, max_parallel_tasks=self._max_parallel_tasks
        )

        temp_root = tempfile.mkdtemp(prefix="pkg_assembly_", dir=BRING_WORKSPACE_FOLDER)

        subtarget_map: Dict[str, Any] = {}
        for index, pkg_config in enumerate(self._assembly.pkg_data):

            pkg = pkg_config["pkg"]
            pkg_name = pkg["name"]
            pkg_index = pkg["index"]

            vars = pkg_config.get("vars", {})

            transform = pkg_config.get("transform", None)
            sub_target = pkg_config.get("target", None)

            frecklet_config = {"type": "install_pkg", "id": f"{pkg_name}.{pkg_index}"}

            frecklet = await self._bring.freckles.create_frecklet(frecklet_config)

            input_values = dict(vars)
            _pkg_name = f"{pkg_index}.{pkg_name}"
            input_values.update({"pkg": _pkg_name})
            input_values["target"] = os.path.join(temp_root, f"pkg_{_pkg_name}_{1}")
            if transform:
                input_values["transform"] = transform

            await frecklet.add_input_set(**input_values)

            task = await frecklet.get_frecklet_task()
            if sub_target:
                subtarget_map[task.id] = sub_target
            await install_tasks.add_tasklet(task)

        await self.add_tasklet(install_tasks)

        task_desc = TaskDesc(name="merge packages", msg="merging packages into target")
        postprocess_task = InstallAssemblyPostprocessTask(
            previous_task=install_tasks,
            target=self._target,
            target_config=self._target_config,
            subtarget_map=subtarget_map,
            task_desc=task_desc,
        )
        await self.add_tasklet(postprocess_task)

    async def execute_tasklets(self, *tasklets: Task) -> None:

        for t in tasklets:
            await t.run_async(raise_exception=True)

    async def create_result_value(self, *tasklets: Task) -> Any:

        return tasklets[-1].result
