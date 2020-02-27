# -*- coding: utf-8 -*-
import os
import sys
from typing import Any, Dict

from appdirs import AppDirs


BRING_APP_DIRS = AppDirs("bring", "frkl")

if not hasattr(sys, "frozen"):
    BRING_MODULE_BASE_FOLDER = os.path.dirname(__file__)
    """Marker to indicate the base folder for the `bring` module."""
else:
    BRING_MODULE_BASE_FOLDER = os.path.join(sys._MEIPASS, "bring")  # type: ignore
    """Marker to indicate the base folder for the `bring` module."""

BRING_CONTEXTS_FOLDER = os.path.join(BRING_APP_DIRS.user_config_dir, "contexts")

BRING_RESOURCES_FOLDER = os.path.join(BRING_MODULE_BASE_FOLDER, "resources")

BRING_DOWNLOAD_CACHE = os.path.join(BRING_APP_DIRS.user_cache_dir, "downloads")
BRING_GIT_CHECKOUT_CACHE = os.path.join(BRING_APP_DIRS.user_cache_dir, "git_checkouts")

BRING_WORKSPACE_FOLDER = os.path.join(BRING_APP_DIRS.user_cache_dir, "workspace")

BRING_PKG_CACHE = os.path.join(BRING_APP_DIRS.user_cache_dir, "pkgs")
DEFAULT_INSTALL_PROFILE_NAME = "all_files"

BRINGISTRY_CONFIG = {
    "prototings": [
        {"prototing_name": "bring.types.pkg", "ting_class": "pkg_ting"},
        {
            "prototing_name": "internal.singletings.context_list",
            "ting_class": "subscrip_tings",
            "prototing_factory": "singleting",
            "prototing": "bring_context_ting",
            "subscription_namespace": "bring.contexts",
            "ting_name": "bring.contexts",
        },
        {
            "prototing_name": "bring.types.config_file_context_maker",
            "ting_class": "text_file_ting_maker",
            "prototing": "bring_context_ting",
            "ting_name_strategy": "basename_no_ext",
            "ting_target_namespace": "bring.contexts",
            "file_matchers": [{"type": "extension", "regex": ".*\\.context$"}],
        },
    ],
    "tings": [],
    "modules": [
        "bring.bring",
        "bring.pkg",
        "bring.pkgs",
        "bring.pkg_resolvers.*",
        "bring.mogrify.*",
        "bring.context",
    ],
    "classes": ["bring.pkg_resolvers.PkgResolver"],
}

# DEFAULT_CONTEXTS = {
#     "executables": {
#         "index": ["/home/markus/projects/tings/bring/repos/executables"],
#         "default_transform_profile": "executables",
#         "metadata_max_age": 3600 * 24,
#         "defaults": get_current_system_info(),
#     }
# }


PKG_RESOLVER_DEFAULTS: Dict[str, Any] = {"metadata_max_age": 3600 * 24}

BRING_METADATA_FOLDER_NAME = ".bring"
BRING_ALLOWED_MARKER_NAME = "bring_allowed"
