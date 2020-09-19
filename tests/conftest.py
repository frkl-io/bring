#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Dummy conftest.py for bring.

    If you don't know what this is for, just leave it empty.
    Read more about conftest.py under:
    https://pytest.org/latest/plugins.html
"""
# import pytest
import os
from collections import Callable

import pytest

from bring.bring import Bring


@pytest.fixture
def bring() -> Bring:

    bring = Bring()
    return bring

@pytest.fixture
def resource_folder() :

    res_folder = os.path.join(os.path.dirname(__file__), "resources")
    return res_folder
