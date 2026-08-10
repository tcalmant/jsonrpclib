#!/usr/bin/env python
# -- Content-Encoding: UTF-8 --
"""
Installation script.

All project metadata lives in ``pyproject.toml`` (the ``[project]`` table),
which is read by setuptools 61+ and by every PEP 517 build front-end. On
Python 3 this file therefore only calls ``setup()`` with no argument.

Python 2.7 ships a setuptools too old to understand that table, so when this
file is executed directly on Python 2 (``python setup.py install``) it supplies
the metadata explicitly. The version is read from ``jsonrpclib/__init__.py`` so
that it is never declared a second time.

:authors: Josh Marshall, Thomas Calmant
:license: Apache License 2.0
"""

import io
import re
import sys

from setuptools import setup

if sys.version_info[0] < 3:
    # Python 2.7: old setuptools cannot read [project] from pyproject.toml, so
    # the metadata is given here. The version is parsed from the package to
    # avoid a second source of truth.
    with io.open("jsonrpclib/__init__.py", encoding="utf-8") as fh:
        _match = re.search(r"__version_info__\s*=\s*\(([^)]*)\)", fh.read())
    _version = ".".join(part.strip() for part in _match.group(1).split(","))

    with io.open("README.md", encoding="utf-8") as fh:
        _long_description = fh.read()

    setup(
        name="jsonrpclib-pelix",
        version=_version,
        license="Apache License 2.0",
        author="Thomas Calmant",
        author_email="thomas.calmant+github@gmail.com",
        url="https://github.com/tcalmant/jsonrpclib/",
        description="JSON-RPC v2.0 client and server for Python 2.7 and 3.6+, "
        "usable with Pelix/iPOPO remote services",
        long_description=_long_description,
        long_description_content_type="text/markdown",
        packages=["jsonrpclib"],
    )
else:
    # Python 3: setuptools reads everything from pyproject.toml
    setup()
