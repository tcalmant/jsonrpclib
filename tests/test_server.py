#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Tests the pooled server

:license: Apache License 2.0
"""

# Standard library
import random
import socket
import threading
import time
import unittest

# JSON-RPC library
from jsonrpclib import ServerProxy
from jsonrpclib.SimpleJSONRPCServer import PooledJSONRPCServer
from jsonrpclib.threadpool import ThreadPool

# ------------------------------------------------------------------------------


def add(a, b):
    """ Basic addition """
    return a + b


def sleep(t):
    start = time.time()
    while time.time() - start < t:
        time.sleep(.1)


class PooledServerTests(unittest.TestCase):
    """
    These tests verify that the pooled server works correctly
    """

    def test_default_pool(self, pool=None, max_time=3):
        """
        Tests the given or the default pool

        :param pool: Thread pool to use
        :param max_time: Max time the sleep test should take
        """
        host_address = socket.gethostbyname("localhost")

        # Setup server
        server = PooledJSONRPCServer((host_address, 0), thread_pool=pool)
        server.register_function(add)
        server.register_function(sleep)

        # Serve in a thread
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()

        try:
            # Find its port
            port = server.socket.getsockname()[1]

            # Make the client
            target_url = "http://{0}:{1}".format(host_address, port)
            client = ServerProxy(target_url)

            # Check calls
            for _ in range(5):
                rand1, rand2 = random.random(), random.random()
                result = client.add(rand1, rand2)
                self.assertEqual(result, rand1 + rand2)

            # Check pauses (using different clients)
            threads = [threading.Thread(target=ServerProxy(
                target_url).sleep, args=(1,)) for _ in range(5)]
            start_time = time.time()
            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()
            end_time = time.time()
            self.assertLessEqual(end_time - start_time, max_time)
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
        pool = ThreadPool(5)
        pool.start()
        try:
            self.test_default_pool(pool)
        finally:
            pool.stop()

    def test_sequencial(self):
        """
        Tests the behaviour with a single-thread pool
        """
        pool = ThreadPool(1, 1)
        pool.start()
        try:
            self.test_default_pool(pool, 6)
        finally:
            pool.stop()
