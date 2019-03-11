#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
aiohttp version of the jsonrpclib client and server

**Work in Progress**
There are still some features to add to match the synchronous version:
* Enhance the use of aiohttp (check if we could reuse a session, ...)

:authors: Thomas Calmant
:copyright: Copyright 2019, Thomas Calmant
:license: Apache License 2.0
:version: 0.5.0

..

    Copyright 2019 Thomas Calmant

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

try:
    # Typing with mypy
    # pylint: disable=W0611
    from typing import Optional
    from ssl import SSLContext

    from jsonrpclib.server_protocol_async import AsyncJsonRpcProtocolHandler
except ImportError:
    pass

# Standard library
import asyncio
import logging

# aiohttp
from aiohttp import web
import aiohttp
import yarl

# Library includes
from .. import Fault
from .abstract_async import AbstractAsyncTransport

# ------------------------------------------------------------------------------

# Module version
__version_info__ = (0, 5, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# Create the logger
_logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Client transport


class AiohttpTransport(AbstractAsyncTransport):
    """
    Asynchronous transport layer based on ``aiohttp``
    """

    @staticmethod
    async def _make_connector(scheme, unix_path, ssl_context):
        # type: (str, Optional[str], SSLContext) -> aiohttp.BaseConnector
        """
        Prepares an ``aiohttp`` connector according to the configuration given
        to the server proxy

        :param scheme: Protocol schema (http or https)
        :param unix_path: Path to the Unix socket (optional)
        :param ssl_context: SSL context to use (optional)
        :return: An ``aiohttp`` connector
        """
        if unix_path:
            if scheme == "http":
                # In Unix mode, we use the path part of the URL (handler)
                # as the path to the socket file
                return aiohttp.UnixConnector(path=unix_path)
        elif scheme == "https":
            return aiohttp.TCPConnector(ssl=ssl_context)
        else:
            return aiohttp.TCPConnector()

        raise IOError(
            "Unhandled combination: UNIX={}, protocol={}".format(
                bool(unix_path), scheme
            )
        )

    def _make_url(self, host, handler):
        # type: (Optional[str], str) -> yarl.URL
        """
        Prepares a URL object according to transport configuration

        :param host: Target host name (unused with Unix socket)
        :param handler: Query path
        """
        if host:
            # Got an absolute path
            return yarl.URL.build(scheme=self._scheme, host=host, path=handler)

        # No host: relative path (Unix mode)
        return yarl.URL.build(path=handler)

    async def request(self, host, handler, request_body, verbose=False):
        # type: (Optional[str], str, str, bool) -> str
        """
        Sends a complete request and parses a response

        :param host: Target host name (unused with Unix socket)
        :param handler: Query path
        :param request_body: String content of the request
        :param verbose: Log verbosity flag
        """
        request = request_body.encode("utf-8")
        url = self._make_url(host, handler)

        # Compute headers
        headers = {
            "user-agent": self._config.user_agent,
            "content-type": self._config.content_type,
        }
        headers.update(self.compute_additional_headers())

        # Prepare the connector (it will be closed at the end of the session
        # life cycle
        connector = await self._make_connector(
            self._scheme, self._unix_path, self._ssl_context
        )

        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                url,
                data=request,
                headers=headers,
                skip_auto_headers=headers.keys(),
            ) as response:
                return await response.text()


# ------------------------------------------------------------------------------
# Server handlers


class AiohttpRequestHandler:
    """
    Basic aiohttp request handler
    """

    def __init__(self, protocol_handler, path):
        # type: (AsyncJsonRpcProtocolHandler, str) -> None
        """
        :param protocol_handler:
        :param path: Path accepted to handle requests
        """
        self._protocol_handler = protocol_handler
        self._path = path

    async def request_handler(self, request):
        # type: (web.BaseRequest) -> web.Response
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


class AiohttpJsonRpcServer:
    """
    Implementation of the asynchronous JSON-RPC server based on aiohttp
    """

    def __init__(self, handler, address, port=0):
        # type: (AiohttpRequestHandler, str, int) -> None
        """
        :param handler: The JSON-RPC request handler
        :param address: Binding address of the server
        :param port: Port to listen to (0 for random port)
        """
        self._stop_event = asyncio.Event()
        self._handler = handler
        self._address = address
        self._port = port
        self._real_port = -1
        self._site = None
        self._runner = None

    def get_port(self):
        # type: () -> int
        """
        Returns the port the server is listening to, or -1 if the server is not
        listening

        :return: The port the server is listening to or -1
        """
        return self._real_port

    def shutdown(self):
        # type: () -> None
        """
        Stops the server
        """
        self._stop_event.set()

    async def async_check_interrupt(self):
        # type: () -> None
        """
        Forces Python to check if a KeyboardInterrupt exception must be raised
        """
        while not self._stop_event.is_set():
            await asyncio.sleep(0.5)

    async def run(self):
        # type: () -> None
        """
        Execution of the server
        """
        self._stop_event.clear()

        server = web.Server(self._handler.request_handler)
        self._runner = web.ServerRunner(server)
        await self._runner.setup()

        self._site = web.TCPSite(self._runner, self._address, self._port)
        await self._site.start()
        self._real_port = self._site._server.sockets[0].getsockname()[1]

        try:
            # Wait the server shutdown message
            await self._stop_event.wait()
        finally:
            # Clean up
            self._real_port = -1
            await self._site.stop()
            await self._runner.shutdown()
