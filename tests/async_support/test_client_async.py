#!/usr/bin/env python3
"""
Tests the asynchronous client implementation with a synchronous server

Only works with Python 3.5+

:license: Apache License 2.0
"""

# Standard library
import asyncio
import unittest

try:
    # aiohttp
    from aiohttp import web
except ImportError:
    raise unittest.SkipTest("async tests require aiohttp")

# JSON-RPC library
import jsonrpclib
from jsonrpclib.jsonrpc_async import AsyncServerProxy
from jsonrpclib.impl.aiohttp_impl import AiohttpTransport

# Tests
from tests.test_compatibility import TestCompatibility
from tests.utilities import UtilityServer


# ------------------------------------------------------------------------------


class AsyncClientWrapper:
    """
    Wrapper to allow calls to the asynchronous from non-async methods
    (i.e. unittest)
    """

    def __init__(self, async_client):
        """
        :param async_client: Underlying asynchronous server proxy
        """
        self.client = async_client
        self.loop = asyncio.get_event_loop()

    def __getattr__(self, item):
        """
        Returns a wrapped asynchronous method
        """
        return AsyncMethodWrapper(self.loop, getattr(self.client, item))

    def __call__(self, *args, **kwargs):
        """
        Returns the result of ``client(...)`` (can be a primitive or a callable)
        """
        return AsyncMethodWrapper(self.loop, self.client(*args, **kwargs))


class AsyncMethodWrapper:
    """
    Wrapper hiding the asynchronous-ity of a method
    """

    def __init__(self, loop, element):
        """
        :param loop: Event loop to use
        :param element: Attribute of the underlying client to call
        """
        self.element = element
        self.loop = loop

    def __call__(self, *args, **kwargs):
        """
        Calls synchronously the asynchronous attribute
        """
        return self.loop.run_until_complete(self.element(*args, **kwargs))

    def __getattr__(self, name):
        """
        Returns a Method object for nested calls
        """
        if name == "__name__":
            return self.element.__name

        return AsyncMethodWrapper(self.loop, getattr(self.element, name))


# ------------------------------------------------------------------------------


class TestAsyncClient(TestCompatibility):
    """
    Tests JSON-RPC compatibility
    """

    def setUp(self):
        """
        Pre-test set up
        """
        # Set up the server
        self.server = UtilityServer().start("", 0)
        self.port = self.server.get_port()

        # Set up the client
        self.history = jsonrpclib.history.History()
        self.client = AsyncClientWrapper(
            AsyncServerProxy(
                "http://127.0.0.1:{0}".format(self.port),
                AiohttpTransport,
                history=self.history,
            )
        )

    def tearDown(self):
        """
        Post-test clean up
        """
        # Close the client
        self.client("close")()

        # Stop the server
        self.server.stop()
