#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Tests the content of the errors sent to the peer.

An unexpected server-side error must not describe itself to the caller: the
exception, its message and the source lines stay in the logs, and the peer only
gets a reference to look them up with. The errors which describe what the
*caller* sent (invalid request, unknown method, invalid parameters) stay
explicit, as they are meant to be acted upon.

:license: Apache License 2.0
"""

# Standard library
import logging
import re
import socket
import threading
import unittest

# JSON-RPC library
import jsonrpclib.config
from jsonrpclib import ProtocolError, ServerProxy
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer
from jsonrpclib.utils import to_bytes

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
        port = self.server.socket.getsockname()[1]

        sock = socket.create_connection((HOST, port))
        sock.settimeout(5)
        try:
            sock.sendall(
                to_bytes(
                    "POST / HTTP/1.1\r\nHost: {0}\r\n"
                    "Content-Type: application/json-rpc\r\n"
                    "Content-Length: 4\r\n\r\n".format(HOST)
                )
                + b"\xff\xfe\xff\xfe"
            )

            raw = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                raw += chunk
        finally:
            sock.close()

        # The error is reported, without describing the server
        body = raw.decode("utf-8", "replace").split("\r\n\r\n", 1)[-1]
        self.assertIsNotNone(
            REF_PATTERN.search(body), "No error reference in {0}".format(body)
        )
        self.assertNotIn(".py", body)
        self.assertNotIn("Traceback", body)
        self.assertNotIn("UnicodeDecodeError", body)


if __name__ == "__main__":
    unittest.main()
