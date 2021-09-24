#!/usr/bin/env python
# -- Content-Encoding: UTF-8 --
"""
Tests the loading of different JSON libraries

:license: Apache License 2.0
"""

import imp
import json
import os
import unittest

import jsonrpclib.jsonlib as jsonlib


TEST_INPUT_MARKER = '"__test_input__"'
TEST_OUTPUT_MARKER = '"__test_output__"'


def _fake_loads(data):
    """
    Fake loads method raising a NotImplementedError when a marker is used
    """
    if data == TEST_INPUT_MARKER:
        raise NotImplementedError
    return {}


def _fake_dumps(obj, encoding="utf8"):  # pylint: disable=unused-argument
    """
    Fake dumps method raising a NotImplementedError when a marker is used
    """
    if obj == TEST_OUTPUT_MARKER:
        raise NotImplementedError

    return ""


class TestJsonLibLoading(unittest.TestCase):
    """
    Tests the jsonlib package, according to environment variables
    """

    def _get_expected_best(self, available):
        # type: (set) -> str
        """
        Returns the name of the expected best JSON library
        (or skips the test)
        """
        expected_best = os.getenv("JSONRPCLIB_TEST_EXPECTED_LIB", "")
        if not expected_best:
            self.skipTest("No expected best JSON library given")

        if expected_best not in available:
            self.skipTest(
                "Expected best library {} is not available".format(
                    expected_best
                )
            )
        return expected_best

    def _check_expected_best(self, required):
        # type: (str) -> str
        """
        Returns the name of the expected best JSON library
        (or skips the test)
        """
        expected_best = os.getenv("JSONRPCLIB_TEST_EXPECTED_LIB", "")
        if not expected_best:
            self.skipTest("No expected best JSON library given")

        if expected_best != required:
            self.skipTest(
                "Expected best library {} is not the tested one ({})".format(
                    expected_best, required
                )
            )
        return expected_best

    def test_best(self):
        """
        Tests the Json library selection
        """
        # Detect available modules
        available = {"json"}

        try:
            import cjson  # pylint: disable=unused-import,import-outside-toplevel

            available.add("cjson")
        except ImportError:
            pass

        try:
            import ujson  # pylint: disable=unused-import,import-outside-toplevel

            available.add("ujson")
        except ImportError:
            pass

        try:
            import simplejson  # pylint: disable=unused-import,import-outside-toplevel

            available.add("simplejson")
        except ImportError:
            pass

        # Check the availability of the expected best handler
        expected_best = self._get_expected_best(available)

        # Test the handler's choice
        imp.reload(jsonlib)
        handler = jsonlib.get_handler()

        # Check its name
        self.assertIn(expected_best.lower(), type(handler).__name__.lower())

        # Ensure the methods getter works
        load_method, dump_method = jsonlib.get_handler_methods()
        if expected_best != "json":
            self.assertIsNot(load_method, json.loads)
            self.assertIsNot(dump_method, json.dumps)

        # Test the method
        obj = {"answer": 42}
        json_obj = dump_method(obj)
        parsed_obj = load_method(json_obj)
        self.assertEqual(obj, parsed_obj, "Invalid object serialization")

    def test_stdlib(self):
        """
        Tests if the standard json module methods are really used
        """
        # Check if the expected best is right
        self._check_expected_best("json")

        try:
            # Force methods to raise an exception
            json.loads = _fake_loads
            json.dumps = _fake_dumps

            # Reload the module
            imp.reload(jsonlib)

            # Check the methods
            load_method, dump_method = jsonlib.get_handler_methods()
            self.assertRaises(
                NotImplementedError, load_method, TEST_INPUT_MARKER
            )
            self.assertRaises(
                NotImplementedError, dump_method, TEST_OUTPUT_MARKER
            )
            self.assertRaises(
                NotImplementedError, dump_method, TEST_OUTPUT_MARKER, "encoding"
            )
        finally:
            # Reload the module
            imp.reload(json)

    def test_cjson(self):
        """
        Tests if the cJson methods are really used
        """
        try:
            import cjson  # pylint: disable=import-outside-toplevel
        except ImportError:
            return self.skipTest("cJson is missing: ignore")

        # Check if the expected best is right
        self._check_expected_best("cjson")

        try:
            # Force methods to raise an exception
            cjson.decode = _fake_loads
            cjson.encode = _fake_dumps

            # Reload the module
            imp.reload(jsonlib)

            # Check the methods
            load_method, dump_method = jsonlib.get_handler_methods()
            self.assertRaises(
                NotImplementedError, load_method, TEST_INPUT_MARKER
            )
            self.assertRaises(
                NotImplementedError, dump_method, TEST_OUTPUT_MARKER
            )
            self.assertRaises(
                NotImplementedError, dump_method, TEST_OUTPUT_MARKER, "encoding"
            )
        finally:
            # Reload the module
            imp.reload(cjson)

    def test_ujson(self):
        """
        Tests if the uJson methods are really used
        """
        try:
            import ujson  # pylint: disable=import-outside-toplevel
        except ImportError:
            return self.skipTest("uJson is missing: ignore")

        # Check if the expected best is right
        self._check_expected_best("ujson")

        try:
            # Force methods to raise an exception
            ujson.loads = _fake_loads
            ujson.dumps = _fake_dumps

            # Reload the module
            imp.reload(jsonlib)

            # Check the handler
            handler = jsonlib.get_handler()
            self.assertIsInstance(handler, jsonlib.UJsonHandler)

            # Check the methods
            load_method, dump_method = jsonlib.get_handler_methods()
            self.assertIs(ujson.loads, _fake_loads)
            self.assertIs(load_method, _fake_loads)
            self.assertRaises(
                NotImplementedError, load_method, TEST_INPUT_MARKER
            )
            self.assertRaises(
                NotImplementedError, dump_method, TEST_OUTPUT_MARKER
            )
            self.assertRaises(
                NotImplementedError, dump_method, TEST_OUTPUT_MARKER, "encoding"
            )
        finally:
            # Reload the module
            imp.reload(ujson)

    def test_simplejson(self):
        """
        Tests if the simplejson methods are really used
        """
        try:
            import simplejson  # pylint: disable=import-outside-toplevel
        except ImportError:
            return self.skipTest("simplejson is missing: ignore")

        # Check if the expected best is right
        self._check_expected_best("simplejson")

        try:
            # Force methods to raise an exception
            simplejson.loads = _fake_loads
            simplejson.dumps = _fake_dumps

            # Reload the module
            imp.reload(jsonlib)

            # Check the methods
            load_method, dump_method = jsonlib.get_handler_methods()
            self.assertRaises(
                NotImplementedError, load_method, TEST_INPUT_MARKER
            )
            self.assertRaises(
                NotImplementedError, dump_method, TEST_OUTPUT_MARKER
            )
            self.assertRaises(
                NotImplementedError, dump_method, TEST_OUTPUT_MARKER, "encoding"
            )
        finally:
            # Reload the module
            imp.reload(simplejson)
