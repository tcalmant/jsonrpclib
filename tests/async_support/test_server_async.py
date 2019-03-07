#!/usr/bin/env python3
"""
Tests the asynchronous server implementation with a synchronous client

Only works with Python 3.5+

:license: Apache License 2.0
"""

# Standard library
import asyncio
import unittest
import threading
import time

try:
    # aiohttp
    from aiohttp import web
except ImportError:
    raise unittest.SkipTest("async tests require aiohttp")

# JSON-RPC library
from jsonrpclib import Fault
from jsonrpclib.server_protocol_async import AsyncJsonRpcProtocolHandler
import jsonrpclib


# ------------------------------------------------------------------------------
# Handler classes


class AsyncRpcRequestHandler:
    """
    Basic aiohttp request handler
    """

    def __init__(self, protocol_handler, path):
        self._protocol_handler = protocol_handler
        self._path = path

    async def request_handler(self, request: web.BaseRequest) -> web.Response:
        """
        Handles an HTTP request
        """
        # Sanity check
        if request.method != "POST":
            return web.HTTPMethodNotAllowed(request.method, ["POST"])

        request_path = request.url.path
        if request_path != self._path:
            return web.HTTPNotFound()

        # Parse the body
        request_data = await request.text()
        response = await self._protocol_handler.handle_request_str(request_data)

        if response is not None:
            result_code = 200
            if isinstance(response, Fault):
                result_code = 500

            # Send the response
            return web.json_response(response, status=result_code)
        else:
            # Send an empty response string
            # This is the expected behaviour for notifications and when
            # handling NoMulticallResult
            return web.json_response(body=b"")


class AsyncJsonRpcServer:
    """
    Implementation of the asynchronous JSON-RPC server based on aiohttp
    """

    def __init__(self, handler: AsyncRpcRequestHandler):
        self._stop_event = asyncio.Event()
        self._handler = handler
        self.port = -1
        self._site = None
        self._runner = None

    def shutdown(self):
        """
        Stops the server
        """
        self._stop_event.set()

    async def async_check_interrupt(self):
        """
        Forces Python to check if a KeyboardInterrupt exception must be raised
        """
        while not self._stop_event.is_set():
            await asyncio.sleep(0.5)

    async def run(self):
        """
        Execution of the server
        """
        server = web.Server(self._handler.request_handler)
        self._runner = web.ServerRunner(server)
        await self._runner.setup()

        self._site = web.TCPSite(self._runner, "127.0.0.1", 0)
        await self._site.start()
        self.port = self._site._server.sockets[0].getsockname()[1]

        # Wait the server shutdown message
        await self._stop_event.wait()

        # Clean up
        await self._site.stop()
        await self._runner.shutdown()


class AsyncServerTests(unittest.TestCase):
    """
    Tests the asynchronous server
    """

    def setUp(self):
        """
        Pre-test set up
        """
        # Define the test handler
        async def pause():
            await asyncio.sleep(0.5)
            return 42

        handler = AsyncJsonRpcProtocolHandler()
        handler.register_function(lambda: "Hello", name="hello")
        handler.register_function(lambda *a: sum(a), name="add")
        handler.register_function(sum)
        handler.register_function(pause)

        # Associate the handler to the protocol wrapper
        self.server = AsyncJsonRpcServer(
            AsyncRpcRequestHandler(handler, "/json-rpc")
        )

        # Loop shared with the server thread
        loop = asyncio.get_event_loop()

        # Thread that will run the server
        def server_thread():
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.server.run())
            finally:
                loop.close()

        # Start the test in a thread
        self.server_thread = threading.Thread(target=server_thread)
        self.server_thread.start()

        # Wait for the server to come up
        while self.server.port == -1:
            time.sleep(0.1)

        # Store the server port
        self.port = self.server.port

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

    def test_server(self):
        """
        Tests the asynchronous server
        """
        # Standard call
        self.assertEqual(self.client.hello(), "Hello")
        self.assertEqual(self.client.add(1, 2, 3), 6)
        self.assertEqual(self.client.sum([1, 2, 3]), 6)
        self.assertEqual(self.client.pause(), 42)

        # Notification
        self.assertIsNone(self.client._notify.hello())
