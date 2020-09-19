import collections
import tempfile
from abc import abstractmethod
from typing import Optional, Mapping, Union, Any, Iterable, List

from frkl.common.exceptions import FrklException
from frkl.tasks.task import Task
from frkl.types.plugins import get_plugin_name
from tings.defaults import NO_VALUE_MARKER
from tings.ting import SimpleTing, TingMeta

def explode_transform_value(data: Any) -> List[Mapping[str, Any]]:

    if not data:
        return []

    if isinstance(data, str):
        result: List[Mapping[str, Any]] = [{"type": data}]
    elif isinstance(data, collections.abc.Mapping):
        if not "type" in data.keys():
            raise FrklException(msg=f"Can't parse 'transform' item: {data}", reason="Missing 'type' key")
        result = [data]
    elif isinstance(data, collections.abc.Iterable):
        result = []
        for item in data:
            if isinstance(item, str):
                result.append({"type": item})
            elif isinstance(item, collections.abc.Mapping):
                if not "type" in item.keys():
                    raise FrklException(msg=f"Can't parse 'transform' item: {item}", reason="Missing 'type' key.")
                result.append(item)
    else:
        raise FrklException(msg=f"Can't parse 'transform' data: {data}", reason=f"Invalid data type '{type(data)}', needs string, iterable or dict")

    return result


class Transformer(Task, SimpleTing):
    """The base class to extend to implement a 'Transformer'.

    A transformer is one part of a pipeline, usually taking an input folder, along other arguments, and providing an
    output folder path as result. Which in turn is used by the subsequent Transformer as input, etc. There are a few special
    cases, for example the 'download' transformer which takes a url as input and provides a path to a file (not folder) as
    output, or the 'extract' transformer which takes an (archive) file as input and provides a folder path as output.

    Currently there is not much validation whether Transformers that are put together fit each others input/output arguments,
    but that will be implemented at some stage. So, for now, it's the users responsibility to assemble transformer
    pipelines that make sense.
    """

    def __init__(self, name: str, meta: TingMeta, **kwargs) -> None:

        self._working_dir: Optional[str] = None
        SimpleTing.__init__(self, name=name, meta=meta)
        Task.__init__(self, **kwargs)

    @property
    def working_dir(self) -> Optional[str]:

        return self._working_dir

    @working_dir.setter
    def working_dir(self, working_dir: str) -> None:

        self._working_dir = working_dir

    def create_temp_dir(self, prefix=None):
        if prefix is None:
            prefix = self._name

        if not self.working_dir:
            raise FrklException(
                msg=f"Can't create temporary directory for transformer {self.name}",
                reason="Working dir not set for mogrifier",
            )

        tempdir = tempfile.mkdtemp(prefix=f"{prefix}_", dir=self.working_dir)
        return tempdir

    def get_msg(self) -> str:

        transformer_name = get_plugin_name(self.__class__)
        return f"executing transformer: {transformer_name}"


class SimpleTransformer(Transformer):
    def __init__(self, name: str, meta: TingMeta, **kwargs):

        Transformer.__init__(self, name=name, meta=meta)

    def requires(self) -> Mapping[str, Union[str, Mapping[str, Any]]]:

        if not hasattr(self.__class__, "_requires"):
            raise FrklException(
                f"Error processing mogrifier '{self.name}'.",
                reason=f"No class attribute '_requires' availble for {self.__class__.__name__}. This is a bug.",
            )

        return self.__class__._requires  # type: ignore

    def provides(self) -> Mapping[str, Union[str, Mapping[str, Any]]]:

        if not hasattr(self.__class__, "_provides"):
            raise FrklException(
                f"Error processing mogrifier '{self.name}'.",
                reason=f"No class attribute '_provides' availble for {self.__class__.__name__}. This is a bug.",
            )

        return self.__class__._provides  # type: ignore

    async def execute_task(self) -> Any:

        result = await self.get_values(raise_exception=True)
        return result

    @property
    def user_input(self):

        result = {}
        for k, v in self.current_input.items():
            if v != NO_VALUE_MARKER:
                result[k] = v

        return result

    def get_user_input(self, key, default=None):

        return self.user_input.get(key, default)

    @abstractmethod
    async def retrieve(self, *value_names: str, **requirements) -> Mapping[str, Any]:
        pass
