# -*- coding: utf-8 -*-
import logging
import os
import shutil
from typing import Any, Mapping, Optional

import anyio
import httpx
from anyio import aopen
from bring.defaults import BRING_DOWNLOAD_CACHE
from bring.mogrify import MogrifierException, SimpleMogrifier
from frkl.common.downloads.cache import calculate_cache_path
from frkl.common.filesystem import ensure_folder
from frkl.common.strings import generate_valid_identifier


log = logging.getLogger("bring")


class DownloadMogrifier(SimpleMogrifier):

    _plugin_name = "download"
    _requires = {"url": "string", "target_file_name": "string", "retries": "int?"}
    _provides = {"file_path": "string"}

    def get_msg(self) -> str:

        result = "downloading file"

        url = self.get_user_input("url")
        if url:
            result = result + f": {url}"

        return result

    async def mogrify(self, *value_names: str, **requirements) -> Mapping[str, Any]:

        download_url = requirements["url"]
        target_file_name = requirements["target_file_name"]

        retries = requirements.get("retries", None)
        if retries is None:
            retries = 3

        if retries < 2:
            retries = 1

        retry_wait = 1

        cache_path = calculate_cache_path(
            base_path=BRING_DOWNLOAD_CACHE, url=download_url
        )

        if not os.path.exists(cache_path):

            ensure_folder(os.path.dirname(cache_path))

            # download to a temp location, in case another process downloads the same url
            temp_name = f"{cache_path}_{generate_valid_identifier()}"

            success = False
            last_error: Optional[Exception] = None

            try:
                client = httpx.AsyncClient()
                try_nr = 1
                while try_nr <= retries and not success:
                    try_nr = try_nr + 1
                    log.debug(f"Downloading url: {download_url} ({try_nr}. try)")

                    async with await aopen(temp_name, "wb") as f:
                        async with client.stream("GET", download_url) as response:
                            try:
                                response.raise_for_status()

                                async for chunk in response.aiter_bytes():
                                    await f.write(chunk)

                                success = True
                            except Exception as e:
                                # TODO: don't retry for certain errors
                                last_error = e
                                log.debug(
                                    f"Failed to download '{download_url}': {e}",
                                    exc_info=True,
                                )

                                status_code = None
                                try:
                                    status_code = e.response.status_code  # type: ignore
                                except Exception:
                                    pass

                                if status_code == 404:
                                    break
                                if try_nr <= retries:
                                    await anyio.sleep(retry_wait)

            finally:
                await client.aclose()

            if not success:
                reason = None
                if last_error:
                    reason = str(last_error)
                raise MogrifierException(
                    self, msg=f"Error downloading '{download_url}'", reason=reason
                )
            if os.path.exists(cache_path):
                os.unlink(temp_name)
            else:
                shutil.move(temp_name, cache_path)

        target_folder = self.create_temp_dir("download_")
        target_path = os.path.join(target_folder, target_file_name)
        ensure_folder(os.path.dirname(target_path))
        shutil.copy2(cache_path, target_path)

        return {"file_path": target_path, "folder_path": target_folder}
