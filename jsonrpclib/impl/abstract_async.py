#!/usr/bin/env python3
"""
Implementations of clients and servers

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
except ImportError:
    pass

# Standard library
import abc

# Library includes
from . import AbstractTransport
import jsonrpclib.config

# ------------------------------------------------------------------------------

# Module version
__version_info__ = (0, 5, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"


# ------------------------------------------------------------------------------


class AbstractAsyncTransport(AbstractTransport, abc.ABC):
    """
    Abstract class for transport implementations
    """

    def __init__(
        self,
        scheme="http",
        unix_path=None,
        ssl_context=None,
        config=jsonrpclib.config.DEFAULT,
    ):
        # type: (str, Optional[str], Optional[SSLContext], jsonrpclib.config.Config) -> None
        """
        :param scheme: Protocol to use (http or https)
        :param scheme: Protocol schema (http or https)
        :param unix_path: Path to the Unix socket (optional)
        :param ssl_context: SSL context to use (optional)
        :param config: JSONRPCLib configuration
        """
        AbstractTransport.__init__(self)

        self._config = config
        self._scheme = scheme or "http"
        self._unix_path = unix_path
        self._ssl_context = ssl_context

    async def close(self):
        # type: () -> None
        """
        Does nothing (API compliance)
        """

    @abc.abstractmethod
    async def request(self, host, handler, request_body, verbose=False):
        # type: (Optional[str], str, str, bool) -> str
        """
        Sends a complete request and parses a response

        :param host: Target host name (unused with Unix socket)
        :param handler: Query path
        :param request_body: String content of the request
        :param verbose: Log verbosity flag
        """
