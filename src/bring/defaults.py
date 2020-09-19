# -*- coding: utf-8 -*-
import os
import sys
from typing import Any, Mapping

from appdirs import AppDirs


bring_app_dirs = AppDirs("bring", "frkl")

if not hasattr(sys, "frozen"):
    BRING_MODULE_BASE_FOLDER = os.path.dirname(__file__)
    """Marker to indicate the base folder for the `bring` module."""
else:
    BRING_MODULE_BASE_FOLDER = os.path.join(
        sys._MEIPASS, "bring"  # type: ignore
    )
    """Marker to indicate the base folder for the `bring` module."""

BRING_RESOURCES_FOLDER = os.path.join(
    BRING_MODULE_BASE_FOLDER, "resources"
)
"""Default folder for resources"""

# cache folders
BRING_DOWNLOAD_CACHE = os.path.join(bring_app_dirs.user_cache_dir, "downloads")
BRING_TEMP_CACHE = os.path.join(bring_app_dirs.user_cache_dir, "temp")
BRING_INDEX_FILES_CACHE = os.path.join(BRING_DOWNLOAD_CACHE, "indexes")
BRING_GIT_CHECKOUT_CACHE = os.path.join(bring_app_dirs.user_cache_dir, "git_checkouts")
# BRING_PKG_CACHE = os.path.join(bring_app_dirs.user_cache_dir, "pkgs")
BRING_PKG_METADATA_CACHE = os.path.join(bring_app_dirs.user_cache_dir, "pkg_metadata")
BRING_PLUGIN_CACHE = os.path.join(bring_app_dirs.user_cache_dir, "plugins")

# package cache settings
BRING_PKG_VERSION_CACHE = os.path.join(bring_app_dirs.user_cache_dir, "pkg_versions")
BRING_PKG_VERSION_DATA_FOLDER_NAME = "version_data"
BRING_PKG_DATA_FOLDER_NAME = "package_data"
BRING_PKG_VERSION_PACKAGES_FOLDER_NAME = "packages"

BRING_PKG_INSTALL_FOLDER = os.path.join(bring_app_dirs.user_cache_dir, BRING_PKG_VERSION_PACKAGES_FOLDER_NAME)

# workspace/result folders
BRING_WORKSPACE_FOLDER = os.path.join(bring_app_dirs.user_cache_dir, "workspace")
BRING_RESULTS_FOLDER = os.path.join(BRING_WORKSPACE_FOLDER, "results")

BRING_VERSION_METADATA_FILE_NAME = "version.json"

BRING_BACKUP_FOLDER = os.path.join(bring_app_dirs.user_data_dir, "backup")

BRING_DEFAULT_LOG_FILE = os.path.join(bring_app_dirs.user_data_dir, "logs", "bring.log")

BRING_VERSIONS_DEFAULT_CACHE_CONFIG: Mapping[str, Any] = {"metadata_max_age": 3600 * 24}

BRING_MODULES_TO_LOAD = [
    "bring.transform.transformers.*",
    "frkl.events.app_events.*",
    "bring.pkg.versions.*"
]

# Default args

VERSION_ARG = {
    "doc": "the version of the package",
    "type": "string",
    "required": True
}
