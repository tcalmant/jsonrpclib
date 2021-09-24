#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Tests the pooled server

:license: Apache License 2.0
"""

# Standard library
import random
import threading
import unittest

# JSON-RPC library
from jsonrpclib import ServerProxy
from jsonrpclib.SimpleJSONRPCServer import PooledJSONRPCServer
from jsonrpclib.threadpool import ThreadPool

# ------------------------------------------------------------------------------


def add(a, b):
    """ Basic addition """
    return a + b


class PooledServerTests(unittest.TestCase):
    """
    These tests verify that the pooled server works correctly
    """

    def test_default_pool(self, pool=None):
        """
        Tests the default pool
        """
        # Setup server
        server = PooledJSONRPCServer(("localhost", 0), thread_pool=pool)
        server.register_function(add)

        # Serve in a thread
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()

        try:
            # Find its port
            port = server.socket.getsockname()[1]

            # Make the client
            client = ServerProxy("http://localhost:{0}".format(port))

            # Check calls
            for _ in range(5):
                rand1, rand2 = random.random(), random.random()
                result = client.add(rand1, rand2)
                self.assertEqual(result, rand1 + rand2)
        finally:
            # Close server
            server.shutdown()
            server.server_close()
            thread.join()

    def test_custom_pool(self):
        """
        Tests the ability to have a custom pool
        """
        # Setup the pool
        pool = ThreadPool(2)
        pool.start()
        try:
            self.test_default_pool(pool)
        finally:
            pool.stop()
