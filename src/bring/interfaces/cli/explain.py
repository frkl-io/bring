import sys
from pathlib import Path

from bring.bring import Bring
from bring.interfaces.cli import cli
import asyncclick as click

from bring.pkg import ResolvePkg, PkgVersion
from bring.transform.pipeline import Pipeline
from frkl.common.formats import INPUT_TYPE
from frkl.common.formats.auto import AutoInput


@cli.group()
@click.pass_context
def explain(ctx):

    pass

@explain.command()
@click.argument("pkg", nargs=1, required=True)
@click.pass_context
async def package(ctx, pkg):

    ai = AutoInput(pkg)
    if ai.input_type == INPUT_TYPE.string:
        raise Exception("XXX")

    content = await ai.get_content_async()
    vt = await ai.get_value_type_async()

    bring: Bring = ctx.obj["bring"]

    pkg = ResolvePkg(tingistry=bring.tingistry, **content)
    import pp
    # pkg.to_dict()
    # pp(pkg.to_dict())

    # path = await pkg.get_version_folder(version="latest", _read_only=False)
    # print(path)

    result = await pkg.install(version="latest")
    print(result)

    # version: PkgVersion = await pkg.find_matching_version(version="latest")

    # pipeline = Pipeline(tingistry=bring.tingistry, task_name="install_pkg")
    #
    # pipeline.add(*version.steps)
    # print(pipeline)
    #
    # result = await pipeline.run_async(raise_exception=True)
    # print(result.result_value)




