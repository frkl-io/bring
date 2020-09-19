# -*- coding: utf-8 -*-
import atexit
import sys
from typing import Iterable

import asyncclick as click


# try:
#     import uvloop
#
#     uvloop.install()
# except Exception:
#     pass
from bring.bring import Bring

click.anyio_backend = "asyncio"


@click.group()
@click.pass_context
async def cli(ctx):

    ctx.obj = {}

    ctx.obj["bring"] = Bring()


from bring.interfaces.cli.explain import explain


if __name__ == "__main__":
    exit_code = cli(_anyio_backend="asyncio")  # pragma: no cover
    sys.exit(exit_code)
