import atexit
import collections
import os
import shutil
from typing import Optional, Any, Mapping, Iterable, Union

from bring.defaults import BRING_WORKSPACE_FOLDER
from bring.transform.transformer import Transformer
from frkl.args.arg import explode_arg_dict
from frkl.common.exceptions import FrklException
from frkl.common.filesystem import ensure_folder
from frkl.common.strings import generate_valid_identifier
from frkl.common.types import isinstance_or_subclass
from frkl.tasks.task import Task
from frkl.tasks.tasks import SimpleTasks
from tings.tingistry import Tingistry


class Pipeline(SimpleTasks):

    def __init__(
        self,
        tingistry: Tingistry,
        working_dir=None,
        **kwargs,
    ):

        self._tingistry: Tingistry = tingistry

        if not kwargs.get("task_name", None):
            kwargs["task_name"] = "bring_pipeline"

        super().__init__(**kwargs)

        if working_dir is None:
            working_dir = os.path.join(BRING_WORKSPACE_FOLDER, "pipelines", self.id)

        self._working_dir = working_dir
        ensure_folder(self._working_dir)

        debug = os.environ.get("DEBUG", "false")
        if debug.lower() != "true":

            def delete_workspace():
                shutil.rmtree(self._working_dir, ignore_errors=True)
            atexit.register(delete_workspace)

        self._target_folder = os.path.join(BRING_WORKSPACE_FOLDER, "results", self.id)
        ensure_folder(os.path.dirname(self._target_folder))

        self._current: Optional[Transformer] = None
        self._last_item: Optional[Transformer] = None

    def create_transformer(self, type: str, **config: Any) -> Transformer:

        ting_name = generate_valid_identifier(prefix="bring.temp.transformers.transformer_", length_without_prefix=8)
        transfomer = self._tingistry.create_ting(type, ting_name=ting_name, publish=False)
        transfomer.set_input(**config)

        return transfomer

    @property
    def working_dir(self):
        return self._working_dir

    def set_input(self, **input_values: Any):

        if not self.tasklets:
            raise FrklException(msg="Can't set input to pipeline.", reason="Non transformer items yet.")

        self.tasklets[0].set_input(**input_values)

    def add(self, *items: Union[Mapping[str, Any], Transformer, Iterable[Union[Mapping[str, Any], Transformer]]]):

        for i in items:
            if isinstance_or_subclass(i, Transformer):
                self.add_transformer(i)
            elif isinstance(i, collections.abc.Mapping):
                transformer = self.create_transformer(**i)
                self.add_transformer(transformer)
            elif isinstance(i, collections.abc.Iterable):
                self.add(*i)
            else:
                raise TypeError(f"Can't add transformer: item has invalid type '{type(i)}'")

    def add_transformer(self, transformer: Transformer) -> None:

        transformer.working_dir = self._working_dir
        if self._current is not None:
            transformer.set_requirements(self._current)

        self.add_tasklet(transformer)  # type: ignore
        self._current = transformer
        self._last_item = self._current

    async def execute_tasklets(self, *tasklets: Task) -> Any:

        for child in tasklets:
            last_result = await child.run_async()
            if not last_result.success:

                if last_result.error is None:
                    raise FrklException(
                        msg=f"Unknown error when executing '{child.__class__.__name__}' mogrifier."
                    )
                else:
                    raise last_result.error

    async def create_result_value(self, *tasklets: Task) -> Any:

        last_task: Task
        for t in tasklets:
            last_task = t

        return last_task.result.result_value

    def provides(self) -> Mapping[str, Mapping[str, Any]]:

        if self._last_item is None:
            raise FrklException(msg="Can't return result value schema.", reason="No items added to pipeline (yet).")

        provides = self._last_item.provides()
        return explode_arg_dict(arg_dict=provides)

