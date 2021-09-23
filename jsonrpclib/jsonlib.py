#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Loads the "best" Python library available for the current interpreter and
provides a single interface for all
"""

try:
    from typing import Any
except ImportError:
    pass

import json
import sys


PYTHON_2 = sys.version_info[0] < 3


class JsonHandler(object):
    """
    Parent class for JSON handlers
    """

    @staticmethod
    def is_loaded():
        # type: () -> bool
        """
        Flag that indicates if an optimized library could be loaded or not
        """
        return False

    def loads(self, json_string):
        # type: (str) -> Any
        """
        Deserializes the given JSON string to a Python object

        :param json_string: A string containing a JSON value/object/array
        :return: The loaded object (dict)/array (list)/value
        """
        return json.loads(json_string)

    def dumps(self, obj, encoding="utf-8"):
        # type: (Any, str) -> str
        """
        Serializes ``obj`` to a JSON formatted string

        :param obj: Object to serialize
        :param encoding: Encoding of the result string
        :return: The JSON string describing the given value
        """
        if PYTHON_2:
            return json.dumps(obj, encoding=encoding)

        return json.dumps(obj)


class CJsonHandler(JsonHandler):
    """
    Handler based on cjson
    """

    try:
        from cjson import (
            decode as loads,
            encode,
        )  # pylint: disable=C0415, E0602

        @staticmethod
        def is_loaded():
            return True

        def dumps(
            self, obj, encoding="utf-8"
        ):  # pylint: disable=unused-argument
            return encode(obj)

    except ImportError:
        pass


class SimpleJsonHandler(JsonHandler):
    """
    Handler based on simplejson
    """

    try:
        from simplejson import loads, dumps  # pylint: disable=C0415, E0602

        @staticmethod
        def is_loaded():
            return True

    except ImportError:
        pass


class UJsonHandler(JsonHandler):
    """
    Handler based on ujson
    """

    try:
        from ujson import (
            loads,
            dumps as _dumps,
        )  # pylint: disable=C0415, E0602

        @staticmethod
        def is_loaded():
            return True

        def dumps(
            self, obj, encoding="utf-8"
        ):  # pylint: disable=unused-argument
            return _dumps(obj)

    except ImportError:
        pass


for handler_class in (UJsonHandler, SimpleJsonHandler, CJsonHandler):
    HANDLER = handler_class()
    if HANDLER.is_loaded():
        try:
            # Check if the library really works
            HANDLER.loads(HANDLER.dumps({"answer": 42}))
        except Exception:
            continue
        else:
            break
else:
    HANDLER = JsonHandler()
