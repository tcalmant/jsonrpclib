#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Tests the CGI request handler

:license: Apache License 2.0
"""

# Standard library
import os
import random
import threading
import unittest

try:
    from http.server import HTTPServer, CGIHTTPRequestHandler
except ImportError:
    from SimpleHTTPServer import HTTPServer
    from CGIHTTPServer import CGIHTTPRequestHandler

# JSON-RPC library
from jsonrpclib import ServerProxy

# ------------------------------------------------------------------------------


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
            server = HTTPServer(("localhost", 0), CGIHTTPRequestHandler)

            # Serve in a thread
            thread = threading.Thread(target=server.serve_forever)
            thread.daemon = True
            thread.start()

            # Find its port
            port = server.socket.getsockname()[1]

            # Make the client
            client = ServerProxy(
                "http://localhost:{0}/cgi-bin/cgi_server.py".format(port)
            )

            # Check calls
            for _ in range(3):
                a, b = random.random(), random.random()
                result = client.add(a, b)
                self.assertEqual(result, a + b)

            # Close server
            server.server_close()
            thread.join()
        finally:
            os.chdir(old_dir)
