import os
from datetime import datetime

import pytest
from tzlocal import get_localzone

from bring.pkg import ResolvePkg, PkgVersion
from frkl.common.formats.auto import AutoInput


@pytest.mark.anyio
async def test_pkg_versions_git_repo(resource_folder, bring):

    now = get_localzone().localize(datetime.now())

    pkg_file = os.path.join(resource_folder, "example-source-1.pkg.br")

    ai = AutoInput(pkg_file)
    content = await ai.get_content_async()

    pkg: ResolvePkg = ResolvePkg(arg_hive=bring.arg_hive, **content)

    vd = await pkg.get_versions_data(metadata_max_age=0)

    match = False
    for v in vd.versions:
        if v.id_vars["version"] == "v1.1.0":
            match = True
        assert v.metadata_timestamp > now

    assert match is True
    assert "latest" in vd.aliases["version"].keys()

@pytest.mark.anyio
async def test_pkg_version_match(resource_folder, bring):

    pkg_file = os.path.join(resource_folder, "example-source-1.pkg.br")

    ai = AutoInput(pkg_file)
    content = await ai.get_content_async()

    pkg: ResolvePkg = ResolvePkg(arg_hive=bring.arg_hive, **content)

    matching_version = await pkg.find_matching_version(version="v1.1.0")
    assert isinstance(matching_version, PkgVersion)
