# -*- coding: utf-8 -*-

"""Main module."""

import logging
from typing import Optional, Any, Mapping

from bring.defaults import BRING_DEFAULT_LOG_FILE, BRING_MODULES_TO_LOAD
from frkl.args.hive import ArgHive
from frkl.events.app_events.mgmt import AppEventManagement
from frkl.types.typistry import Typistry
from tings.tingistry import Tingistry

log = logging.getLogger("bring")


class Bring(object):
    """The central management class in bring.

    Contains indexes, and methods to manage packages (update metadata, download, etc.)
    """

    def __init__(self):

        self._config: Mapping[str, Any] = {
            "event_targets": [{"type": "terminal"}],
            "log_file": BRING_DEFAULT_LOG_FILE
        }

        self._typistry: Optional[Typistry] = None
        self._tingistry: Optional[Tingistry] = None
        self._arg_hive: Optional[ArgHive] = None
        self._app_events: Optional[AppEventManagement] = None

    def get_config_value(self, key: str) -> Any:
        return self._config.get(key, None)

    @property
    def tingistry(self):

        if self._tingistry is None:
            self._tingistry = Tingistry("bring", typistry=self.typistry)
        return self._tingistry


    @property
    def typistry(self):

        if self._typistry is None:
            self._typistry = Typistry(
                modules=[BRING_MODULES_TO_LOAD]
            )
        return self._typistry

    @property
    def arg_hive(self):

        if self._arg_hive is None:
            self._arg_hive = ArgHive(typistry=self.typistry)
        return self._arg_hive

    def app_events(self) -> AppEventManagement:
        if self._app_events is None:
            self._app_events = AppEventManagement(
                base_topic="bring",
                target_configs=self.get_config_value("event_targets"),
                typistry=self.typistry,
                log_file=self.get_config_value("log_file"),
                logger_name="bring",
                )
        return self._app_events
