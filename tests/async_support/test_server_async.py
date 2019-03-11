#!/usr/bin/env python3
"""
Tests the asynchronous server implementation with a synchronous client

Only works with Python 3.5+

:license: Apache License 2.0
"""

# Standard library
import asyncio
import threading
import time

# JSON-RPC library
from jsonrpclib.server_protocol_async import AsyncJsonRpcProtocolHandler
from jsonrpclib.impl.aiohttp_impl import (
    AiohttpJsonRpcServer,
    AiohttpRequestHandler,
)
import jsonrpclib

# Tests
from tests.test_compatibility import TestCompatibility
from tests.utilities import register_server_functions


# ------------------------------------------------------------------------------
# Test case


class AsyncServerTests(TestCompatibility):
    """
    Tests the asynchronous server
    """

    def setUp(self):
        """
        Pre-test set up
        """

        # Define an asynchronous pause method
        async def pause():
            await asyncio.sleep(0.5)
            return 42

        # Prepare the handler with common functions, plus the asynchronous one
        handler = AsyncJsonRpcProtocolHandler()
        register_server_functions(handler)
        handler.register_function(pause)

        # Associate the handler to the protocol wrapper
        self.server = AiohttpJsonRpcServer(
            AiohttpRequestHandler(handler, "/json-rpc"), "127.0.0.1", 0
        )

        # Loop shared with the server thread
        loop = asyncio.get_event_loop()

        # Thread that will run the server
        def server_thread():
            # Don't do that if you don't know what you are doing
            # Here, the loop is used in the main thread only with
            # loop.call_soon_threadsafe()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.server.run())

        # Start the test in a thread
        self.server_thread = threading.Thread(target=server_thread)
        self.server_thread.start()

        # Wait for the server to come up
        while self.server.get_port() == -1:
            time.sleep(0.1)

        # Store the server port
        self.port = self.server.get_port()

        # Set up the client
        self.history = jsonrpclib.history.History()
        self.client = jsonrpclib.ServerProxy(
            "http://localhost:{0}/json-rpc".format(self.port),
            history=self.history,
        )

    def tearDown(self):
        """
        Post-test clean up
        """
        # Close the client
        self.client("close")()

        # Stop the server
        loop = asyncio.get_event_loop()
        loop.call_soon_threadsafe(self.server.shutdown)

        # Wait for the server to stop
        self.server_thread.join()
        self.server_thread = None

    def test_async_call(self):
        """
        Tests the call to an asynchronous method
        """
        self.assertEqual(self.client.pause(), 42)
