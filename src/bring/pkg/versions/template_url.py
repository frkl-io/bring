# -*- coding: utf-8 -*-
import itertools
import os
from typing import Any, Dict, Iterable, List, Mapping, Union

from bring.pkg import VersionSource, PkgVersion
from frkl.common.downloads.cache import calculate_cache_location_for_url


class TemplateUrlResolver(VersionSource):
    """A package type to resolve packages whose artifacts are published with static urls that can be templated.

    All values of all template variables are combined with each of the other template variables to create a matrix of possible combinations.
    In some cases some of those combinations are not valid, and lead to a url that does not resolve to a file to download. At this time,
    there is nothing that can be done about it and the user will see an error message.

    Examples:
        - binaries.kubectl
        - binaries.helm
    """

    _plugin_name: str = "template_url"
    _plugin_supports: str = "template_url"

    def __init__(self, **config: Any):
        super().__init__(**config)

    # def _name(self):
    #
    #     return "template-url"

    # def _supports(self) -> List[str]:
    #
    #     return ["template-url"]

    def get_pkg_args(self) -> Mapping[str, Any]:

        return {
            # "template_values": {
            #     "type": "dict",
            #     "required": True,
            #     "doc": "A map with the possible template var names as keys, and all allowed values for each key as value.",
            # },
            "url": {
                "type": "string",
                "required": True,
                "doc": "The templated url string, using '{{' and '}}' as template markers.",
            },
        }

    async def _retrieve_pkg_versions(self, **source_input) -> Iterable[PkgVersion]:

        url = source_input["url"]

        steps = [
            {"type": "download", "url": url}
        ]
        version = PkgVersion(steps=steps, id_vars={})

        # template_values = source_details["template_values"]
        #
        # keys, values = zip(*template_values.items())
        #
        # versions = [dict(zip(keys, v)) for v in itertools.product(*values)]
        #
        # _version_list: List[PkgVersion] = []
        # for version in versions:
        #     # print(version)
        #     # print(source_details["url"])
        #     # url = process_string_template(source_details["url"], copy.copy(version))
        #     # print(url)
        #     url = source_details["url"]
        #     target_file_name = os.path.basename(url)
        #
        #     _vd: Dict[str, Any] = {}
        #     _vd["vars"] = version
        #     _vd["metadata"] = {"url": url}
        #     _vd["steps"] = [
        #         {"type": "download", "url": url, "target_file_name": target_file_name}
        #     ]
        #     _version_list.append(PkgVersion(**_vd))
        #
        # return {"versions": _version_list}

    def get_artefact_mogrify(
        self, source_details: Mapping[str, Any], version: PkgVersion
    ) -> Union[Mapping, Iterable]:

        url: str = version.metadata.get("url")  # type: ignore

        match = False
        for ext in [".zip", "tar.gz", "tar.bz2"]:
            if url.endswith(ext):
                match = True
                break

        if match:
            return {"type": "extract"}
        else:
            return {"type": "file"}

    def _get_unique_source_type_id(self) -> str:

        url = self.pkg_input_values["url"]
        id = calculate_cache_location_for_url(url, sep="_")
        return id
