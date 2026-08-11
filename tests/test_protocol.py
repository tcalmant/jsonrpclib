#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Tests the protocol helpers of the client: the analysis of a response
(check_for_errors) and the request predicates (isbatch, isnotification).

check_for_errors decides what a client does with what a server sent it, so
every one of its branches is driven by the peer.

:license: Apache License 2.0
"""

# Standard library
import unittest

# JSON-RPC library
from jsonrpclib import AppError, ProtocolError
from jsonrpclib.jsonrpc import check_for_errors, isbatch, isnotification

# ------------------------------------------------------------------------------


def response(error):
    """
    Prepares a JSON-RPC response holding the given error

    :param error: The content of the "error" member
    :return: A response dictionary
    """
    return {"jsonrpc": "2.0", "id": 1, "error": error}


# ------------------------------------------------------------------------------


class CheckForErrorsTests(unittest.TestCase):
    """
    Checks the analysis of the responses of a server
    """

    def test_no_response(self):
        """
        Tests that an empty response is returned as is (notification)
        """
        for empty in (None, "", {}, []):
            self.assertEqual(empty, check_for_errors(empty))

    def test_valid_response(self):
        """
        Tests that a valid response is returned as is
        """
        valid = {"jsonrpc": "2.0", "id": 1, "result": 42}
        self.assertIs(valid, check_for_errors(valid))

    def test_not_a_dict(self):
        """
        Tests that a response which is not a dictionary is refused
        """
        self.assertRaises(TypeError, check_for_errors, ["not", "a", "dict"])
        self.assertRaises(TypeError, check_for_errors, "not a dict")

    def test_unsupported_version(self):
        """
        Tests that a response of a newer JSON-RPC version is refused
        """
        self.assertRaises(
            NotImplementedError,
            check_for_errors,
            {"jsonrpc": "3.0", "id": 1, "result": 42},
        )

    def test_no_result_nor_error(self):
        """
        Tests that a response with neither a result nor an error is refused
        """
        self.assertRaises(
            ValueError, check_for_errors, {"jsonrpc": "2.0", "id": 1}
        )

    def test_predefined_error(self):
        """
        Tests that a JSON-RPC error code is reported as a ProtocolError
        """
        for code in (-32700, -32600, -32601, -32602, -32603, -32000):
            try:
                check_for_errors(response({"code": code, "message": "Oops"}))
            except ProtocolError as ex:
                self.assertTupleEqual((code, "Oops"), ex.args[0])
            else:
                self.fail("No error raised for code {0}".format(code))

    def test_application_error(self):
        """
        Tests that a code outside of the pre-defined range is reported as an
        AppError, which gives access to the data of the error
        """
        error = {"code": 42, "message": "Custom", "data": {"detail": "here"}}
        try:
            check_for_errors(response(error))
        except AppError as ex:
            code, message, data = ex.args[0]
            self.assertEqual(42, code)
            self.assertEqual("Custom", message)
            self.assertDictEqual({"detail": "here"}, data)
        else:
            self.fail("No error raised")

    def test_application_error_without_data(self):
        """
        Tests an application error which doesn't give any data
        """
        try:
            check_for_errors(response({"code": 42, "message": "Custom"}))
        except AppError as ex:
            self.assertIsNone(ex.args[0][2])
        else:
            self.fail("No error raised")

    def test_jabsorb_trace(self):
        """
        Tests the fallback on the "trace" member, used by jabsorb, when the
        error has no message
        """
        try:
            check_for_errors(response({"code": 42, "trace": "The trace"}))
        except AppError as ex:
            self.assertEqual("The trace", ex.args[0][1])
        else:
            self.fail("No error raised")

    def test_error_without_message_nor_trace(self):
        """
        Tests an error which has neither a message nor a trace
        """
        try:
            check_for_errors(response({"code": 42}))
        except AppError as ex:
            self.assertEqual("<no error message>", ex.args[0][1])
        else:
            self.fail("No error raised")

    def test_single_entry_error(self):
        """
        Tests an error described by a single entry, without a code: its content
        is used as is
        """
        try:
            check_for_errors(response({"reason": "Because"}))
        except ProtocolError as ex:
            self.assertEqual("Because", ex.args[0])
        else:
            self.fail("No error raised")

    def test_raw_error(self):
        """
        Tests an error which is neither a code/message pair nor a single entry
        """
        for error in ("Plain string", {"a": 1, "b": 2}, ["a", "b"]):
            try:
                check_for_errors(response(error))
            except ProtocolError as ex:
                self.assertEqual(error, ex.args[0])
            else:
                self.fail("No error raised for {0}".format(error))

    def test_null_error(self):
        """
        Tests that a null error (JSON-RPC 1.0 success) is not an error
        """
        valid = {"id": 1, "result": 42, "error": None}
        self.assertIs(valid, check_for_errors(valid))


# ------------------------------------------------------------------------------


class RequestPredicatesTests(unittest.TestCase):
    """
    Checks the predicates describing a request
    """

    def test_isbatch(self):
        """
        Tests the detection of a batch call
        """
        batch = [
            {"jsonrpc": "2.0", "method": "a", "id": 1},
            {"jsonrpc": "2.0", "method": "b", "id": 2},
        ]
        self.assertTrue(isbatch(batch))
        self.assertTrue(isbatch(tuple(batch)))

        # A single request, even in a list of one, is a batch
        self.assertTrue(isbatch(batch[:1]))

    def test_isbatch_refuses(self):
        """
        Tests what is not considered as a batch call
        """
        not_batches = (
            {"jsonrpc": "2.0", "method": "a", "id": 1},  # not a list
            "a string",
            [],  # empty
            [42],  # not a dictionary
            [{"method": "a", "id": 1}],  # no version marker
            [{"jsonrpc": "1.0", "method": "a", "id": 1}],  # before 2.0
        )
        for candidate in not_batches:
            self.assertFalse(
                isbatch(candidate), "{0} taken as a batch".format(candidate)
            )

    def test_isbatch_invalid_version(self):
        """
        Tests that a non-numeric version is refused
        """
        self.assertRaises(ProtocolError, isbatch, [{"jsonrpc": "not-a-number"}])

    def test_isnotification(self):
        """
        Tests the detection of a notification: a request without an ID, or
        with a null one
        """
        self.assertTrue(isnotification({"method": "a"}))
        self.assertTrue(isnotification({"method": "a", "id": None}))

    def test_isnotification_with_an_id(self):
        """
        Tests that a request with an ID is not a notification.

        0 and an empty string are valid IDs here (see the 1.1 release notes),
        even though the server also treats an empty ID as a notification.
        """
        self.assertFalse(isnotification({"method": "a", "id": 1}))
        self.assertFalse(isnotification({"method": "a", "id": 0}))
        self.assertFalse(isnotification({"method": "a", "id": ""}))


if __name__ == "__main__":
    unittest.main()
