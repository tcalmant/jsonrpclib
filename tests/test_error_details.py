#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Tests which errors are reported to the peer, and what they contain.

An unexpected server-side error must not describe itself to the caller: the
exception, its message and the source lines stay in the logs, and the peer only
gets a reference to look them up with. The errors which describe what the
*caller* sent (invalid request, unknown method, invalid parameters) stay
explicit, as they are meant to be acted upon.

Interruptions (KeyboardInterrupt, SystemExit) are not errors of the call: they
must stop the server instead of being reported as a result.

:license: Apache License 2.0
"""

# Standard library
import json
import logging
import re
import socket
import threading
import unittest

# JSON-RPC library
import jsonrpclib.config
from jsonrpclib import Fault, ProtocolError, ServerProxy
from jsonrpclib.SimpleJSONRPCServer import (
    SimpleJSONRPCDispatcher,
    SimpleJSONRPCServer,
)
from jsonrpclib.utils import to_bytes

# Tests utilities
from tests.utilities import raw_post, response_body

# ------------------------------------------------------------------------------

HOST = socket.gethostbyname("localhost")

# The secret must never reach the peer
SECRET = "hunter2"

# Reference added to the message sent to the peer
REF_PATTERN = re.compile(r"Server error \(ref: ([0-9a-f]+)\)")


def boom():
    """
    A method which fails, like any real method eventually does
    """
    raise ValueError("db password is {0}".format(SECRET))


class ListHandler(logging.Handler):
    """
    Keeps the log records, to check what the server logged
    """

    def __init__(self):
        """
        Sets up members
        """
        logging.Handler.__init__(self)
        self.records = []

    def emit(self, record):
        """
        Stores the record
        """
        self.records.append(record)

    def get_text(self):
        """
        Returns the formatted content of all records, including the tracebacks

        :return: The text of the stored log records
        """
        return "\n".join(self.format(record) for record in self.records)


# ------------------------------------------------------------------------------


class ErrorDetailsTests(unittest.TestCase):
    """
    Checks what a caller learns about a server-side error
    """

    def setUp(self):
        """
        Tests initialization
        """
        self.server = None
        self.thread = None

        # Catch what the server logs (assertLogs doesn't exist on Python 2.7)
        self.log_handler = ListHandler()
        self.logger = logging.getLogger("jsonrpclib.SimpleJSONRPCServer")
        self.logger.addHandler(self.log_handler)

        # Keep the logs of the tests quiet
        self.old_propagate = self.logger.propagate
        self.logger.propagate = False

    def tearDown(self):
        """
        Post-test clean up
        """
        self.logger.removeHandler(self.log_handler)
        self.logger.propagate = self.old_propagate

        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(5)
            self.server = None
            self.thread = None

    def make_client(self, config=None):
        """
        Starts a server and returns a client for it

        :param config: The configuration of the server and of the client
        :return: A ServerProxy talking to the server
        """
        config = config or jsonrpclib.config.Config()

        self.server = SimpleJSONRPCServer(
            (HOST, 0), logRequests=False, config=config
        )
        self.server.register_function(boom)
        self.server.register_function(lambda x, y: x + y, "add")

        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

        port = self.server.socket.getsockname()[1]
        return ServerProxy("http://{0}:{1}".format(HOST, port), config=config)

    def call_error(self, method, *args):
        """
        Calls a method which is expected to fail and returns the error

        :param method: A bound remote method
        :return: The (code, message) tuple of the error
        """
        try:
            method(*args)
        except ProtocolError as ex:
            return ex.args[0][0], ex.args[0][1]

        self.fail("No error raised")

    def test_exception_details_not_sent(self):
        """
        Tests that a failing method doesn't describe its exception to the peer
        """
        client = self.make_client()
        code, message = self.call_error(client.boom)

        self.assertEqual(-32603, code)

        # Nothing about the exception, the source or the file
        self.assertNotIn(SECRET, message)
        self.assertNotIn("ValueError", message)
        self.assertNotIn(".py", message)
        self.assertNotIn("Traceback", message)

    def test_error_reference_is_logged(self):
        """
        Tests that the reference given to the peer is in the logs, along with
        the details of the error
        """
        client = self.make_client()
        _, message = self.call_error(client.boom)

        match = REF_PATTERN.search(message)
        self.assertIsNotNone(match, "No error reference in {0}".format(message))

        # The details are kept on the server side, under the same reference
        logged = self.log_handler.get_text()
        self.assertIn(match.group(1), logged)
        self.assertIn(SECRET, logged)
        self.assertIn("ValueError", logged)
        self.assertIn("Traceback", logged)

    def test_exception_details_opt_in(self):
        """
        Tests that the details can be sent back on request
        """
        config = jsonrpclib.config.Config(send_exception_details=True)
        client = self.make_client(config)
        code, message = self.call_error(client.boom)

        self.assertEqual(-32603, code)
        self.assertIsNotNone(REF_PATTERN.search(message))
        self.assertIn(SECRET, message)
        self.assertIn("ValueError", message)

    def test_caller_errors_stay_explicit(self):
        """
        Tests that the errors describing what the caller sent are unchanged:
        they are meant to be acted upon by the caller
        """
        client = self.make_client()

        # Unknown method
        code, message = self.call_error(client.no_such_method)
        self.assertEqual(-32601, code)
        self.assertIn("no_such_method", message)

        # Invalid parameters
        code, message = self.call_error(client.add, 1, 2, 3)
        self.assertEqual(-32602, code)
        self.assertIn("Invalid parameters", message)

    def test_request_handler_error(self):
        """
        Tests that an error raised while handling the request itself doesn't
        disclose the server paths (it is answered by the do_POST error handler,
        here with a body which is not valid UTF-8)
        """
        self.make_client()
        body = response_body(
            raw_post(
                HOST,
                self.server.socket.getsockname()[1],
                "Content-Type: application/json-rpc\r\nContent-Length: 4\r\n",
                b"\xff\xfe\xff\xfe",
            )
        )

        # The error is reported, without describing the server
        self.assertIsNotNone(
            REF_PATTERN.search(body), "No error reference in {0}".format(body)
        )
        self.assertNotIn(".py", body)
        self.assertNotIn("Traceback", body)
        self.assertNotIn("UnicodeDecodeError", body)

    def post_body(self, body):
        """
        Sends a raw request body to the test server

        :param body: The body of the request, as a string
        :return: The body of the response, as a string
        """
        raw_body = to_bytes(body)
        return response_body(
            raw_post(
                HOST,
                self.server.socket.getsockname()[1],
                "Content-Type: application/json-rpc\r\n"
                "Content-Length: {0}\r\n".format(len(raw_body)),
                raw_body,
            )
        )

    def test_parse_error_quotes_a_bounded_part(self):
        """
        Tests that an unparsable request is not quoted back in full
        """
        self.make_client()

        padding = "x" * 20000
        answer = self.post_body(
            '{{"jsonrpc":"2.0","id":1,"method":"m","params":["{0}"'.format(
                padding
            )
        )

        # The answer must not grow with the request
        self.assertLess(len(answer), 1024)
        self.assertNotIn(padding, answer)

        # The caller still learns what was wrong, and what was left out
        self.assertIn("-32700", answer)
        self.assertIn("characters", answer)

    def test_invalid_request_quotes_a_bounded_part(self):
        """
        Tests that a request without a version marker is not quoted back in
        full either
        """
        self.make_client()

        padding = "y" * 20000
        answer = self.post_body(
            '{{"method":"ping","params":["{0}"]}}'.format(padding)
        )

        self.assertLess(len(answer), 1024)
        self.assertNotIn(padding, answer)
        self.assertIn("-32600", answer)
        self.assertIn("characters", answer)

    def test_short_request_is_quoted_as_is(self):
        """
        Tests that a small request is still quoted back entirely: the point is
        to bound the answer, not to hide what the caller sent
        """
        self.make_client()

        answer = self.post_body('{"jsonrpc":"2.0","id":1,')

        self.assertIn('{\\"jsonrpc\\":\\"2.0\\",\\"id\\":1,', answer)
        self.assertNotIn("characters)", answer)


# ------------------------------------------------------------------------------


class InterruptionTests(unittest.TestCase):
    """
    Checks that an interruption isn't turned into a JSON-RPC error.

    A KeyboardInterrupt or a SystemExit means the server is being stopped: it
    must travel up to the server loop, where a normal exception is caught and
    reported to the caller.
    """

    def setUp(self):
        """
        Tests initialization
        """
        self.dispatcher = SimpleJSONRPCDispatcher()
        self.dispatcher.register_function(boom, "boom")

        for exception in (KeyboardInterrupt, SystemExit):
            self.dispatcher.register_function(
                self.make_raiser(exception), exception.__name__
            )

    @staticmethod
    def make_raiser(exception):
        """
        Returns a method raising the given exception

        :param exception: An exception class
        :return: A method raising it
        """

        def raiser():
            raise exception("Stopping")

        return raiser

    def test_dispatch_lets_interruptions_through(self):
        """
        Tests that _dispatch doesn't convert an interruption into a Fault
        """
        for exception in (KeyboardInterrupt, SystemExit):
            self.assertRaises(
                exception,
                self.dispatcher._dispatch,
                exception.__name__,
                [],
            )

    def test_dispatch_reports_errors(self):
        """
        Tests that a normal exception is still reported as a Fault
        """
        fault = self.dispatcher._dispatch("boom", [])
        self.assertIsInstance(fault, Fault)
        self.assertEqual(-32603, fault.faultCode)

    def test_marshaled_dispatch_lets_interruptions_through(self):
        """
        Tests that the whole dispatch chain lets an interruption reach the
        request handler, which lets it reach the server loop
        """
        for exception in (KeyboardInterrupt, SystemExit):
            request = json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": exception.__name__,
                    "params": [],
                }
            )
            self.assertRaises(
                exception, self.dispatcher._marshaled_dispatch, request
            )


if __name__ == "__main__":
    unittest.main()
