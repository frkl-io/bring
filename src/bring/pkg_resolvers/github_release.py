# -*- coding: utf-8 -*-
import copy
import logging
import re
import time
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

import arrow
import httpx
from bring.pkg_resolvers import HttpDownloadPkgResolver
from frtls.exceptions import FrklException
from httpx import Headers


DEFAULT_URL_REGEXES = [
    "https://github.com/.*/releases/download/v(?P<version>.*)/.*-v(?P=version)-(?P<arch>[^-]*)-(?P<os>[^.]*)\\..*$"
]

# "https://github.com/.*/releases/download/v(?P<version>.*)/.*-v(?P=version)-(?P<arch>[^-]*)-(?P<os>[^.]*)\\.(?P<type>.*)$"

log = logging.getLogger("bring")


class GithubRelease(HttpDownloadPkgResolver):

    last_github_limit_details = None

    @classmethod
    def get_github_limits(cls) -> Dict[str, Any]:

        r = httpx.get("https://api.github.com/rate_limit")
        data = r.json()

        details = {}
        details["limit"] = data["limit"]
        details["remaining"] = data["remaining"]
        details["reset_epoch"] = data["reset"]
        gmtime = time.gmtime(details["reset_epoch"])
        reset = arrow.get(gmtime)
        details["reset"] = reset

        cls.last_github_limit_details = details
        return details

    @classmethod
    def secs_to_github_limit_reset(cls) -> Optional[int]:

        if not cls.last_github_limit_details:
            cls.get_github_limits()

        now = arrow.now()
        delta = cls.last_github_limit_details["reset"] - now
        secs = delta.total_seconds()
        return secs

    def __init__(self, config: Optional[Mapping[str, Any]] = None):

        self._github_username = None
        self._github_token = None
        if config:
            self._github_username = config.get("github_username", None)
            self._github_token = config.get("github_access_token", None)

        super().__init__(config=config)

    def _supports(self) -> List[str]:

        return ["github-release"]

    def get_unique_source_id(self, source_details: Dict) -> str:

        github_user = source_details.get("user_name")
        repo_name = source_details.get("repo_name")

        artefact_name = source_details.get("artefact_name", "")

        if artefact_name:
            artefact_name = f"_{artefact_name}"

        return f"{github_user}_{repo_name}{artefact_name}"

    async def _retrieve_versions(
        self, source_details: Union[str, Dict]
    ) -> Union[Tuple[List, Dict], List]:

        github_user = source_details.get("user_name")
        repo_name = source_details.get("repo_name")

        repo_url = f"https://api.github.com/repos/{github_user}/{repo_name}/releases"

        req_headers = Headers({"Accept": "application/vnd.github.v3+json"})
        async with httpx.AsyncClient() as client:
            req = {"headers": req_headers}
            if self._github_username and self._github_token:
                req["auth"] = (self._github_username, self._github_token)

            r = await client.get(repo_url, **req)
            releases = r.json()

        github_details = {}
        github_details["limit"] = int(r.headers.get("X-RateLimit-Limit"))
        github_details["remaining"] = int(r.headers.get("X-RateLimit-Remaining"))
        github_details["reset_epoch"] = int(r.headers.get("X-RateLimit-Reset"))

        gmtime = time.gmtime(github_details["reset_epoch"])
        reset = arrow.get(gmtime)

        log.info(
            f"github requests remaining: {github_details['remaining']}, reset: {reset} ({reset.humanize()})"
        )

        github_details["reset"] = reset
        GithubRelease.last_github_limit_details = github_details

        if r.status_code != 200:

            if github_details["remaining"] == 0:
                reason = f"Github rate limit exceeded (quota: {github_details['limit']}, reset: {reset.humanize()})"
                if not self._github_username or not self._github_token:
                    solution = f"Set both 'github_user' and 'github_access_token' configuration values to make authenticated requests to GitHub and get a higher quota."
                else:
                    solution = f"Wait until your limit is reset: {str(reset)}"
            else:
                reason = r.text
                solution = None

            raise FrklException(
                msg=f"Can't retrieve metadata for github release '{github_user}/{repo_name}.",
                reason=reason,
                solution=solution,
            )

        url_regexes = source_details.get("url_regex", None)
        if not url_regexes:
            url_regexes = DEFAULT_URL_REGEXES
        elif isinstance(url_regexes, str):
            url_regexes = [url_regexes]

        log.debug(f"Regexes for {github_user}/{repo_name}: {url_regexes}")
        result = []
        aliases = {}
        for release in releases:

            version_data = self.parse_release_data(release, url_regexes, aliases)
            if version_data:
                result.extend(version_data)

        return result, aliases

    def parse_release_data(
        self, data: Dict, url_regexes: List, aliases: Dict
    ) -> Union[Tuple[List[Dict], Dict], List[Dict]]:

        result = []
        version = data["name"]
        prerelease = data["prerelease"]
        created_at = data["created_at"]
        tarball_url = data["tarball_url"]
        zipball_url = data["zipball_url"]

        meta = {
            "orig_version_name": version,
            "prerelease": prerelease,
            "source_tarball_url": tarball_url,
            "source_zipball_url": zipball_url,
            "release_date": created_at,
        }

        for asset in data["assets"]:
            browser_download_url = asset["browser_download_url"]
            log.debug(f"trying url: {browser_download_url}")
            vars = None
            for regex in url_regexes:
                match = re.search(regex, browser_download_url)

                if match is not None:
                    vars = match.groupdict()
                    break

            if vars is None:
                log.debug("No match")
                continue

            missing = []
            for k, v in vars.items():
                if v is None:
                    missing.append(k)
            for m in missing:
                vars.pop(m)
            log.debug(f"Matched vars: {vars}")

            if "version" in vars.keys():
                vers = vars["version"]
                if not prerelease:
                    if "stable" not in aliases.setdefault("version", {}).keys():
                        aliases["version"]["stable"] = vers
                    if "latest" not in aliases.setdefault("version", {}).keys():
                        aliases["version"]["latest"] = vers
                else:
                    if "pre-release" not in aliases.setdefault("version", {}).keys():
                        aliases["version"]["pre-release"] = vers

            asset_name = asset["name"]
            content_type = asset["content_type"]
            size = asset["size"]

            m = copy.copy(meta)
            m["asset_name"] = asset_name
            m["content_type"] = content_type
            m["size"] = size
            m["url"] = browser_download_url
            vars["_meta"] = m

            result.append(vars)

        return result

    def get_download_url(self, version: Dict[str, str], source_details: Dict):

        return version["_meta"]["url"]
