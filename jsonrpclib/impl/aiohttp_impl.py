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
    import jsonrpclib.history
except ImportError:
    pass

# Standard library
import logging

# aiohttp
import aiohttp
import yarl

# Library includes
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
