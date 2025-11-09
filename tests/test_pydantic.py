#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Tests the handling of Pydantic BaseModel arguments

:license: Apache License 2.0
"""

# Standard library
import socket
import threading
import unittest

from jsonrpclib.jsonrpc import ProtocolError

try:
    # Pydantic
    from pydantic import BaseModel, Field
except ImportError:
    raise unittest.SkipTest("Pydantic not found.")

# JSON-RPC library
from jsonrpclib import ServerProxy
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer

# ------------------------------------------------------------------------------

class Argument(BaseModel):
    name: str
    value: int


class Result(BaseModel):
    response: str
    universal_answer: bool = False
    value: int = Field(description="Query", gt=0, lt=50)


def handler(arg):
    # type: (Argument) -> Result
    """
    Handler test function
    """
    return Result(
        response="{} answered {}".format(arg.name, arg.value),
        value=arg.value,
        universal_answer=arg.value == 42,
    )


# ------------------------------------------------------------------------------

HOST = socket.gethostbyname("localhost")


class PydanticTests(unittest.TestCase):
    """
    These tests ensures that the server and client work with Pydantic models
    """

    def test_all_pydantic(self):
        """ Test with valid data """
        # Prepare the server
        srv = SimpleJSONRPCServer((HOST, 0))
        srv.register_function(handler, "test")

        thread = threading.Thread(target=srv.serve_forever)
        thread.daemon = True
        thread.start()

        try:
            # Find its port
            port = srv.socket.getsockname()[1]

            # Make the client
            target_url = "http://{0}:{1}".format(HOST, port)
            client = ServerProxy(target_url)

            arg = Argument(name="foo", value=42)
            result = client.test(arg)
            self.assertIsInstance(result, Result)
            self.assertEqual(arg.value, result.value)
            self.assertTrue(result.universal_answer)

            arg = Argument(name="foo", value=20)
            result = client.test(arg)
            self.assertIsInstance(result, Result)
            self.assertEqual(arg.value, result.value)
            self.assertFalse(result.universal_answer)
        finally:
            srv.shutdown()
            srv.server_close()
            thread.join(5)

    def test_invalid(self):
        """
        Test Pydantic when the client uses an invalid value
        """
# Prepare the server
        srv = SimpleJSONRPCServer((HOST, 0))
        srv.register_function(handler, "test")

        thread = threading.Thread(target=srv.serve_forever)
        thread.daemon = True
        thread.start()

        try:
            # Find its port
            port = srv.socket.getsockname()[1]

            # Make the client
            target_url = "http://{0}:{1}".format(HOST, port)
            client = ServerProxy(target_url)

            arg = Argument(name="foo", value=100)
            try:
                client.test(arg)
            except ProtocolError as e:
                # Something when wrong on the other side, as expected
                self.assertEqual(-32603, e.args[0][0])
            else:
                self.fail("No error raised")
        finally:
            srv.shutdown()
            srv.server_close()
            thread.join(5)
