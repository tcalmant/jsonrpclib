#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Tests the server & client in Unix socket mode (when available)

:license: Apache License 2.0
"""

# Standard library
import os
import random
import socket
import threading
import unittest

# JSON-RPC library
from jsonrpclib import ServerProxy
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer

# ------------------------------------------------------------------------------

if not hasattr(socket, "AF_UNIX"):
    raise unittest.SkipTest("Unix sockets are not supported here.")


class UnixSocketTests(unittest.TestCase):
    """
    These tests ensures that the server and client work in Unix socket mode
    """

    def test_full_path(self):
        """
        Starts a Unix socket server, giving with a full path to the socket
        """
        # Ensure we have a new socket
        socket_name = "/tmp/test_server.socket"
        if os.path.exists(socket_name):
            os.remove(socket_name)

        # Use a random int as result
        awaited_result = random.randint(1, 100)

        try:
            # Prepare the server
            srv = SimpleJSONRPCServer(
                socket_name, address_family=socket.AF_UNIX
            )
            srv.register_function(lambda: awaited_result, "test")

            # Run the server in a thread
            thread = threading.Thread(target=srv.serve_forever)
            thread.start()

            try:
                # Run the request (use '.' as hostname)
                client = ServerProxy("unix+http://./{}".format(socket_name))
                result = client.test()
                self.assertEqual(result, awaited_result)
            finally:
                # Stop the server
                srv.shutdown()
                srv.server_close()
                thread.join(5)
        finally:
            # Clean up
            try:
                os.remove(socket_name)
            except IOError:
                pass

    def test_host_only(self):
        """
        Starts a Unix socket server, giving with a relative path to the socket
        """
        # Ensure we have a new socket
        socket_name = "test_local.socket"
        if os.path.exists(socket_name):
            os.remove(socket_name)

        # Use a random int as result
        awaited_result = random.randint(1, 100)

        try:
            # Prepare the server
            srv = SimpleJSONRPCServer(
                socket_name, address_family=socket.AF_UNIX
            )
            srv.register_function(lambda: awaited_result, "test")

            # Run the server in a thread
            thread = threading.Thread(target=srv.serve_forever)
            thread.start()

            try:
                # Run the request
                client = ServerProxy("unix+http://{}".format(socket_name))
                result = client.test()
                self.assertEqual(result, awaited_result)
            finally:
                # Stop the server
                srv.shutdown()
                srv.server_close()
                thread.join(5)
        finally:
            # Clean up
            try:
                os.remove(socket_name)
            except IOError:
                pass
