#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Defines a simple JSON-RPC server based on a Unix socket.

This server is defined in a separate server as it is not available on all
platforms  (namely, Windows out of the WSL)

:authors: Thomas Calmant
:copyright: Copyright 2018, Thomas Calmant
:license: Apache License 2.0
:version: 0.3.2

..

    Copyright 2018 Thomas Calmant

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

# Standard library
import socket

try:
    # Python 3
    # pylint: disable=F0401,E0611
    import socketserver
except (ImportError, AttributeError):
    # Python 2 or IronPython
    # pylint: disable=F0401,E0611
    import SocketServer as socketserver

try:
    # Windows
    import fcntl
except ImportError:
    # Other systems
    # pylint: disable=C0103
    fcntl = None

# jsonrpclib classes
from jsonrpclib.SimpleJSONRPCServer import (
    SimpleJSONRPCDispatcher,
    SimpleJSONRPCRequestHandler,
)
import jsonrpclib.config


class UnixJSONRPCServer(socketserver.UnixStreamServer, SimpleJSONRPCDispatcher):
    """
    JSON-RPC server (and dispatcher), based on a Unix socket
    """

    # This is not available on Unix sockets
    allow_reuse_address = False

    # pylint: disable=C0103
    def __init__(
        self,
        addr,
        requestHandler=SimpleJSONRPCRequestHandler,
        logRequests=True,
        encoding=None,
        config=jsonrpclib.config.DEFAULT,
    ):
        """
        Sets up the server and the dispatcher

        :param addr: The server listening address
        :param requestHandler: Custom request handler
        :param logRequests: Flag to(de)activate requests logging
        :param encoding: The dispatcher request encoding
        :param config: A JSONRPClib Config instance
        """
        # Set up the dispatcher fields
        SimpleJSONRPCDispatcher.__init__(self, encoding, config)

        # Prepare the server configuration
        # logRequests is used by SimpleXMLRPCRequestHandler
        self.logRequests = False
        self.json_config = config

        # Work on the request handler
        class RequestHandlerWrapper(requestHandler, object):
            """
            Wraps the request handle to have access to the configuration
            """
            def __init__(self, *args, **kwargs):
                """
                Constructs the wrapper after having stored the configuration
                """
                self.config = config
                self.disable_nagle_algorithm = False
                super(RequestHandlerWrapper, self).__init__(*args, **kwargs)

        # Set up the server
        socketserver.UnixStreamServer.__init__(
            self, addr, RequestHandlerWrapper
        )

        # Windows-specific
        if fcntl is not None and hasattr(fcntl, 'FD_CLOEXEC'):
            flags = fcntl.fcntl(self.fileno(), fcntl.F_GETFD)
            flags |= fcntl.FD_CLOEXEC
            fcntl.fcntl(self.fileno(), fcntl.F_SETFD, flags)
