import json
import os
import pathlib
import pickle
import shutil
import tempfile
from abc import ABCMeta, abstractmethod
from datetime import datetime
from typing import Optional, Iterable, Mapping, Any, Set, Dict, List, MutableMapping, Union, Tuple
import logging
import arrow
from anyio import open_file
from deepdiff import DeepHash
from tzlocal import get_localzone

from bring.defaults import BRING_TEMP_CACHE, BRING_VERSIONS_DEFAULT_CACHE_CONFIG, \
    BRING_PKG_VERSION_CACHE, BRING_VERSION_METADATA_FILE_NAME, BRING_RESULTS_FOLDER, BRING_PKG_VERSION_DATA_FOLDER_NAME, \
    BRING_PKG_METADATA_CACHE
from bring.transform.pipeline import Pipeline
from frkl.args.arg import RecordArg, explode_arg_dict
from frkl.args.hive import ArgHive
from frkl.common.async_utils import wrap_async_task
from frkl.common.dicts import get_seeded_dict
from frkl.common.exceptions import FrklException
from frkl.common.filesystem import ensure_folder
from frkl.common.regex import replace_var_names_in_obj
from frkl.common.strings import from_camel_case
from frkl.common.types import isinstance_or_subclass
from tings.tingistry import Tingistry

try:
    # we always want the same hashes, independent of whethre mmh3 is installed or not
    import mmh3  # noqa
except:
    raise FrklException(msg="murmur hash library not installed", solution="Make sure you have the 'mmh3' python library is installed in your environment.")


log = logging.getLogger("bring")


class PkgVersion(object):
    def __init__(
        self,
        steps: Iterable[Mapping[str, Any]],
        id_vars: Mapping[str, Any],
        aliases: Optional[Mapping[str, Mapping[Any, Any]]] = None,
        metadata_timestamp: Optional[datetime]=None,
        metadata: Optional[Mapping[str, Any]] = None,
    ):
        self._steps: List[Mapping[str, Any]] = replace_var_names_in_obj(steps, repl_dict=id_vars, ignore_missing_keys=True)  # type: ignore

        self._id_vars: Mapping[str, Any] = id_vars

        if aliases is None:
            aliases = {}
        else:
            aliases = dict(aliases)
        self._aliases: MutableMapping[str, Mapping[Any, Any]] = aliases

        if metadata is None:
            metadata = {}
        self._metadata: Mapping[str, Any] = metadata

        if metadata_timestamp is None:
            tz = get_localzone()
            metadata_timestamp = tz.localize(datetime.now())
        self._metadata_timestamp: datetime = metadata_timestamp

        self._steps_hash: Optional[str] = None

    @property
    def steps(self) -> List[Mapping[str, Any]]:
        return self._steps

    @steps.setter
    def steps(self, steps: Iterable[Mapping[str, Any]]):
        self._steps = list(steps)

    @property
    def id_vars(self) -> Mapping[str, Any]:
        """Retrun the vars that identify this version."""
        return self._id_vars

    @property
    def id_vars_names(self) -> Iterable[str]:
        return self.id_vars.keys()

    @property
    def metadata(self) -> Mapping[str, Any]:
        return self._metadata

    # @property
    # def var_names(self) -> Set[str]:
    #     return self._var_names

    @property
    def metadata_timestamp(self) -> datetime:
        return self._metadata_timestamp

    @property
    def id(self) -> str:
        """Return the id of this version.

        The id consists of the hash for
        """
        if self._steps_hash is None:
            hashes = DeepHash(self.steps)
            self._steps_hash = str(hashes[self.steps])
        return self._steps_hash

    def match_score(self, **version_input: Any) -> int:

        if not self._aliases:
            translated_input = version_input
        else:
            translated_input = {}
            for k, v in version_input.items():
                if k not in self._aliases.keys():
                    translated_input[k] = v
                    continue

                if v not in self._aliases[k].keys():
                    translated_input[k] = v
                    continue

                translated_input[k] = self._aliases[k][v]

        score = 0
        for k, v in self.id_vars.items():
            if k in translated_input.keys():
                if v != translated_input[k]:
                    return 0
                else:
                    score = score + 1

        return score

    def __hash__(self):

        return hash(self.id)

    def __eq__(self, other):

        if not isinstance_or_subclass(other, PkgVersion):
            return False

        return self.id == other.id

    def __repr__(self):

        return f"{self.__class__.__name__}(vars={self.id_vars} steps={self.steps})"

    def to_dict(self) -> Mapping[str, Any]:

        result: Dict[str, Any] = {}
        result["steps"] = self._steps
        result["vars"] = self._id_vars
        result["id"] = self.id
        result["aliases"] = self._aliases
        result["metadata"] = self._metadata
        result["metadata_timestamp"] = str(self._metadata_timestamp)
        return result


def get_version_sources_factory(tingistry: Tingistry):

    _pkg_type_conf: MutableMapping[str, Any] = {}
    for k, v in os.environ.items():
        k = k.lower()
        if not k.startswith("bring_"):
            continue
        _pkg_type_conf[k[6:]] = v

    _pkg_type_conf["tingistry"] = tingistry

    return tingistry.typistry.register_plugin_factory(
        "version_sources", VersionSource, singleton=False, use_existing=True, **_pkg_type_conf
    )


class VersionSource(metaclass=ABCMeta):
    """Model to manage package source details."""

    def __init__(self, tingistry: Tingistry, **pkg_input_values: Any):

        self._tingistry: Tingistry = tingistry
        self._arg_hive: ArgHive = self._tingistry.arg_hive

        self._source_id: Optional[str] = None

        self._pkg_input_values: Mapping[str, Any] = pkg_input_values
        self._validated_pkg_input_values: Optional[Mapping[str, Any]] = None

        self._versions: Optional[Iterable[PkgVersion]] = None
        self._version_args_dict: Optional[Mapping[str, Mapping[str, Any]]] = None

        self._source_args: Optional[RecordArg] = None

        # self._version_var_names: Optional[Set[str]] = None
        # self._all_var_names: Optional[Set[str]] = None

        self._aliases: Optional[Mapping[str, Mapping[Any, Any]]] = None
        self._cache_config: Optional[Mapping[str, Any]]=None

        self._cache_dir = os.path.join(
            BRING_PKG_METADATA_CACHE, from_camel_case(self.__class__.__name__)
        )

    @property
    def tingistry(self) -> Tingistry:

        return self._tingistry

    @property
    def pkg_args(self) -> RecordArg:

        if self._source_args is None:
            self._source_args = self._arg_hive.create_record_arg(self.get_pkg_args())
        return self._source_args

    @property
    def pkg_input_values(self) -> Mapping[str, Any]:
        return self._pkg_input_values

    @property
    def validated_pkg_input_values(self) -> Mapping[str, Any]:
        """Return validated values that are used to configure this VersionSource object.

        This makes sure the raw input for this package adheres to the input schema required by the sub-classed
        VersionSource type, as well as fills in defaults etc.
        """

        if self._validated_pkg_input_values is None:
            self._validated_pkg_input_values = self.pkg_args.validate(self.pkg_input_values, raise_exception=True)
        return self._validated_pkg_input_values

    async def get_versions(self) -> Iterable[PkgVersion]:

        if self._versions is not None:
            return self._versions

        cached_versions = await self.get_cached_versions(
            cache_config=self._cache_config,
        )
        if cached_versions:
            self._versions, self._version_args_dict = cached_versions

        else:

            try:
                result = await self._retrieve_pkg_versions(**self.validated_pkg_input_values)

                if not isinstance(result, Tuple):
                    self._versions = result
                    args_dict = {}
                else:
                    if not result:
                        self._versions = []
                        args_dict = {}
                    elif isinstance(result[-1], PkgVersion):
                        self._versions = list(result)
                        args_dict = {}
                    else:
                        self._versions = result[0]
                        args_dict = result[1]

                self._version_args_dict = explode_arg_dict(args_dict)

                # TODO: validate against args?
                await self.write_versions_cache(self._versions, self._version_args_dict)

            except (Exception) as e:
                log.debug(f"Can't retrieve versions for pkg: {e}")
                log.debug(
                    f"Error retrieving versions in resolver '{self.__class__.__name__}': {e}",
                    exc_info=True,
                )
                raise e

        return self._versions

    async def find_matching_version(self, **input_values: Any) -> Optional[PkgVersion]:
        """Find the version of this package that matches the provided input."""

        matches: Dict[int, List[PkgVersion]] = {}
        for version in await self.get_versions():
            match_score = version.match_score(**input_values)
            matches.setdefault(match_score, []).append(version)

        max_match = max(matches.keys())

        if not max_match:
            raise NotImplementedError()

        _v = matches[max_match]
        if len(_v) != 1:
            raise FrklException(msg=f"Can't find matchig package version for input values: {input_values}", reason=f"More than one matches found: {_v}")

        return _v[0]

    async def find_version_and_get_folder(self, _read_only: bool=False, _version_base_dir: Optional[str]=None, **input_values: Any) -> str:

        version = await self.find_matching_version(**input_values)
        if not version:
            raise FrklException(msg=f"Can't get version dir for package.", reason=f"No version found for values: {input_values}")
        return await self.get_version_folder(version=version, read_only=_read_only, version_base_dir=_version_base_dir)

    def calculate_version_folder_base_path(self, version: PkgVersion, version_base_dir: Optional[str]=None) -> str:

        if version_base_dir is None:
            version_base_dir = os.path.join(BRING_PKG_VERSION_CACHE, from_camel_case(self.__class__.__name__))

        return os.path.join(version_base_dir, version.id)

    async def get_version_folder(self, version: PkgVersion, read_only: bool = False) -> str:
        """Get the path to a local folder that contains all files for the specified version of a package.

        This method should work for all child classes, but can be overwritten if necessary (e.g. to save disk-space (check out 'git_repo' for an example).

        If you only collect metadata, set 'read_only' to True, which will
        save disk space as well as improve performance.
        If 'read_only' is set, you can't rely on the folder to be available
        after *bring* finished. Set to True if that is necessary.

        Args:
            version (PkgVersion): the version object
            read_only (bool): indicate whether the resulting folder will be written to or not

        Returns:
            str: the path to the version folder
        """

        version_base_path = self.calculate_version_folder_base_path(version, version_base_dir=None)
        version_path = os.path.join(version_base_path, BRING_PKG_VERSION_DATA_FOLDER_NAME)

        if not os.path.exists(version_path):

            # install that version
            pipeline = Pipeline(tingistry=self.tingistry, task_name="create_version_folder")
            pipeline.add(*version.steps)

            pipeline_result = await pipeline.run_async(raise_exception=True)
            path = pipeline_result.result_value["folder_path"]

            ensure_folder(version_base_path)
            shutil.move(path, version_path)

            # write metadata
            md_file = os.path.join(version_base_path, BRING_VERSION_METADATA_FILE_NAME)
            tz = get_localzone()
            created = str(tz.localize(datetime.now()))
            md = version.to_dict()
            md["created"] = created
            async with await open_file(md_file, "w") as f:
                await f.write(json.dumps(md))

        if read_only:
            return version_path

        result_base = tempfile.mkdtemp(prefix=f"{version.id}_", dir=BRING_RESULTS_FOLDER)
        result_dir = os.path.join(result_base, "data")

        shutil.copytree(version_path, result_dir)
        return result_dir

    async def write_versions_cache(self, versions: Iterable[PkgVersion], args: Mapping[str, Mapping[str, Any]]):

        metadata_file = self._get_cache_path()

        ensure_folder(BRING_TEMP_CACHE)
        temp_file = tempfile.mkstemp(dir=BRING_TEMP_CACHE)[1]

        pickled = pickle.dumps((versions, args))
        try:
            async with await open_file(temp_file, "wb") as f:
                await f.write(pickled)

            ensure_folder(os.path.dirname(metadata_file))
            shutil.move(temp_file, metadata_file)
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)


    async def get_version_args_dict(self) -> Mapping[str, Mapping[str, Any]]:

        await self.get_versions()
        return self._version_args_dict

    @abstractmethod
    async def _retrieve_pkg_versions(self) -> Union[Iterable[PkgVersion], Tuple[Iterable[PkgVersion], Mapping[str, Union[str, Mapping[str, Any]]]]]:
        """Method to override to retrieve the actual version data if no cached data can be found.

        This can either return a list of PkgVersion items, or a tuple of such a list and a dictionary describing some or
        all of the arguments required to pick a version. If the latter is not supplied, bring will try to create it
        automatically.
        """

        pass

    @abstractmethod
    def get_pkg_args(self) -> Mapping[str, Mapping[str, Any]]:
        """A dictionary describing which arguments are necessary to create a package of this type."""
        pass

    def get_unique_source_id(self) -> str:
        """Return a calculated unique id for a package.

        Implement your own '_get_unique_type_source_id' method for a type specific, meaningful id.
        If that method is not overwritten, a 'deephash' of the source dictionary is used.

        This is used mainly for caching purposes.
        """

        if self._source_id is None:
            self._source_id = f"{from_camel_case(self.__class__.__name__)}_{self._get_unique_source_type_id()}"
        return self._source_id

    def _get_unique_source_type_id(self):
        """Overwrite to return a meaningful (for the source type) unique id."""

        # TODO: maybe include version of bring or the versionSource into hash?
        hashes = DeepHash(self.validated_pkg_input_values)
        return hashes[self.validated_pkg_input_values]

    def _get_cache_path(
        self,
    ):

        path = os.path.join(self._cache_dir, self.get_unique_source_id())
        return path

    def _get_cache_details(
        self
    ) -> Mapping[str, Any]:

        result: Dict[str, Any] = {}
        path = self._get_cache_path()
        result["path"] = path
        cache_file = pathlib.Path(path)

        if not cache_file.exists():
            result["exists"] = False
            return result

        if not cache_file.is_file():
            raise Exception(f"Cache file should be a file, but isn't: {path}")

        file_stat = cache_file.stat()
        file_size = file_stat.st_size
        if file_size == 0:
            os.unlink(cache_file)
            result["exists"] = False
            return result

        result["exists"] = True
        result["size"] = file_size
        modification_time = datetime.fromtimestamp(file_stat.st_mtime)
        tz = get_localzone()
        result["modified"] = tz.localize(modification_time)

        return result

    async def get_cached_versions(
        self,
        cache_config: Optional[Mapping[str, Any]]=None,
        skip_validity_check: bool = False,
    ) -> Optional[Tuple[Iterable[PkgVersion], Mapping[str, Mapping[str, Any]]]]:

        if not skip_validity_check:

            if cache_config is None:
                cache_config = BRING_VERSIONS_DEFAULT_CACHE_CONFIG
            else:
                cache_config = get_seeded_dict(BRING_VERSIONS_DEFAULT_CACHE_CONFIG, cache_config)

            if not self.metadata_is_valid(
                cache_config=cache_config,
            ):
                return None

        details = self._get_cache_details()

        if not details["exists"]:
            return None

        path = details["path"]

        async with await open_file(path, "rb") as f:
            content = await f.read()

        cached_data: Tuple[Iterable[PkgVersion], Mapping[str, Mapping[str, Any]]] = pickle.loads(content)
        return cached_data

    def metadata_is_valid(
        self,
        cache_config: Optional[Mapping[str, Any]],
    ) -> bool:

        cache_details = self._get_cache_details()

        if cache_details["exists"] is False:
            return False

        metadata_max_age = cache_config["metadata_max_age"]
        modified = cache_details["modified"]
        file_date = arrow.get(modified)
        now = arrow.now(get_localzone())

        diff = now - file_date

        if diff.seconds > metadata_max_age:
            log.debug(f"Metadata cache expired for: {cache_details['path']}")

            return False

        # content: PkgMetadata = await self.get_cached_metadata(source_details=_source_details, config=override_config, _source_id=_source_id, skip_validity_check=True)
        #
        # if content.source_details != _source_details:
        #     return False

        return True

    def to_dict(self) -> Dict[str, Any]:

        result = {
            "steps": self.steps,
            "transform": self.transform,
            "input_values": self.pkg_input_values
        }

        return result
