#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Selects the best parser for JSON and defines load and dump methods

:authors: Josh Marshall, Thomas Calmant
:copyright: Copyright 2019, Thomas Calmant
:license: Apache License 2.0
:version: 0.5.0

..

    Copyright 2019 Thomas Calmant

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

try:
    # Typing with mypy
    # pylint: disable=W0611
    from typing import Any
except ImportError:
    pass

# Standard library
import logging
import sys

# ------------------------------------------------------------------------------

# Module version
__version_info__ = (0, 5, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# Create the logger
_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# JSON library import

try:
    # pylint: disable=F0401,E0611
    # Using cjson
    import cjson

    _logger.debug("Using cjson as JSON library")

    # Declare cjson methods
    def jdumps(obj, encoding="utf-8"):
        # type: (Any, str) -> str
        """
        Serializes ``obj`` to a JSON formatted string, using cjson.
        """
        return cjson.encode(obj)

    def jloads(json_string):
        # type: (str) -> Any
        """
        Deserializes ``json_string`` (a string containing a JSON document)
        to a Python object, using cjson.
        """
        return cjson.decode(json_string)


except ImportError:
    # pylint: disable=F0401,E0611
    # Use json or simplejson
    try:
        import json
    except ImportError:
        try:
            import simplejson as json
        except ImportError:
            _logger.error("No supported JSON library found")
            raise ImportError(
                "You must have the cjson, json, or simplejson "
                "module(s) available."
            )
        else:
            _logger.debug("Using simplejson as JSON library")
    else:
        _logger.debug("Using json as JSON library")

    # Declare json methods
    if sys.version_info[0] < 3:

        def jdumps(obj, encoding="utf-8"):
            # type: (Any, str) -> str
            """
            Serializes ``obj`` to a JSON formatted string.
            """
            # Python 2 (explicit encoding)
            return json.dumps(obj, encoding=encoding)

    else:
        # Python 3
        def jdumps(obj, encoding="utf-8"):
            # type: (Any, str) -> str
            """
            Serializes ``obj`` to a JSON formatted string.
            """
            # Python 3 (the encoding parameter has been removed)
            return json.dumps(obj)

    def jloads(json_string):
        # type: (str) -> Any
        """
        Deserializes ``json_string`` (a string containing a JSON document)
        to a Python object.
        """
        return json.loads(json_string)
