#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Tests the CGI request handler

:license: Apache License 2.0
"""

from __future__ import print_function

# Standard library
import os
import random
import socket
import threading
import sys
import unittest


if sys.version_info >= (3, 15):
    raise unittest.SkipTest("CGI support has been removed in Python 3.15")

try:
    from http.server import HTTPServer, CGIHTTPRequestHandler
except ImportError:
    from BaseHTTPServer import HTTPServer  # type: ignore
    from CGIHTTPServer import CGIHTTPRequestHandler  # type: ignore

# JSON-RPC library
from jsonrpclib import ServerProxy

# ------------------------------------------------------------------------------

HOST = socket.gethostbyname("localhost")


class CGIHandlerTests(unittest.TestCase):
    """
    These tests verify that the CGI request handler works correctly
    """

    def test_server(self):
        """
        Tests the CGI request handler
        """
        # Move the parent directory of "cgi-bin"
        old_dir = os.getcwd()
        try:
            # Setup server
            os.chdir(os.path.dirname(__file__))
            server = HTTPServer((HOST, 0), CGIHTTPRequestHandler)

            # Serve in a thread
            thread = threading.Thread(target=server.serve_forever)
            thread.daemon = True
            thread.start()

            # Find its port
            port = server.socket.getsockname()[1]

            # Make the client
            client = ServerProxy(
                "http://{0}:{1}/cgi-bin/cgi_server.py".format(HOST, port)
            )

            # Check call
            for _ in range(2):
                rand1, rand2 = random.random(), random.random()
                result = client.add(rand1, rand2)
                self.assertEqual(result, rand1 + rand2)

            # Close server
            server.shutdown()
            server.server_close()
            thread.join()
        finally:
            os.chdir(old_dir)
