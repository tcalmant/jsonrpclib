#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Defines a request dispatcher, a HTTP request handler, a HTTP server and a
CGI request handler.

:authors: Josh Marshall, Thomas Calmant
:copyright: Copyright 2019, Thomas Calmant
:license: Apache License 2.0
:version: 0.4.0

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

# We use print() in the CGI request handler
from __future__ import print_function

# Standard library
import logging
import socket
import sys
import traceback

try:
    # Python 3
    # pylint: disable=F0401,E0611
    import xmlrpc.server as xmlrpcserver
    import socketserver
except (ImportError, AttributeError):
    # Python 2 or IronPython
    # pylint: disable=F0401,E0611
    import SimpleXMLRPCServer as xmlrpcserver
    import SocketServer as socketserver

SimpleXMLRPCRequestHandler = xmlrpcserver.SimpleXMLRPCRequestHandler
CGIXMLRPCRequestHandler = xmlrpcserver.CGIXMLRPCRequestHandler

try:
    # Windows
    import fcntl
except ImportError:
    # Other systems
    # pylint: disable=C0103
    fcntl = None

try:
    # Python with support for Unix socket
    _AF_UNIX = socket.AF_UNIX
except AttributeError:
    # Unix sockets are not supported, use a dummy value
    _AF_UNIX = -1

# Local modules
from jsonrpclib import Fault
from jsonrpclib.server_protocol import JsonRpcProtocolHandler, NoMulticallResult
import jsonrpclib.config
import jsonrpclib.ipv6utils as ipv6utils
import jsonrpclib.utils as utils
import jsonrpclib.threadpool

# ------------------------------------------------------------------------------

# Module version
__version_info__ = (0, 4, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# Prepare the logger
_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------


class SimpleJSONRPCRequestHandler(SimpleXMLRPCRequestHandler):
    """
    HTTP request handler.

    The server that receives the requests must have a json_config member,
    containing a JSONRPClib Config instance
    """
    def do_POST(self):
        """
        Handles POST requests
        """
        if not self.is_rpc_path_valid():
            self.report_404()
            return

        # Retrieve the configuration
        config = getattr(self.server, 'json_config', jsonrpclib.config.DEFAULT)

        try:
            # Read the request body
            max_chunk_size = 10 * 1024 * 1024
            size_remaining = int(self.headers["content-length"])
            chunks = []
            while size_remaining:
                chunk_size = min(size_remaining, max_chunk_size)
                raw_chunk = self.rfile.read(chunk_size)
                if not raw_chunk:
                    break
                chunks.append(raw_chunk)
                size_remaining -= len(chunks[-1])
            data = utils.from_bytes(b''.join(chunks))

            try:
                # Decode content
                data = self.decode_request_content(data)
                if data is None:
                    # Unknown encoding, response has been sent
                    return
            except AttributeError:
                # Available since Python 2.7
                pass

            # Execute the method
            response = self.server.marshaled_dispatch(
                data, getattr(self, '_dispatch', None)
            )

            # No exception: send a 200 OK
            self.send_response(200)
        except:
            # Exception: send 500 Server Error
            self.send_response(500)
            err_lines = traceback.format_exception(*sys.exc_info())
            trace_string = "{0} | {1}".format(
                err_lines[-2].splitlines()[0].strip(), err_lines[-1])
            fault = jsonrpclib.Fault(-32603, "Server error: {0}"
                                     .format(trace_string), config=config)
            _logger.exception("Server-side error: %s", fault)
            response = fault.response()

        if response is None:
            # Avoid to send None
            response = ''

        # Convert the response to the valid string format
        response = utils.to_bytes(response)

        # Send it
        self.send_header("Content-type", config.content_type)
        self.send_header("Content-length", str(len(response)))
        self.end_headers()
        if response:
            self.wfile.write(response)

# ------------------------------------------------------------------------------


class SimpleJSONRPCServer(socketserver.TCPServer, JsonRpcProtocolHandler):
    """
    JSON-RPC server (and dispatcher)
    """
    # This simplifies server restart after error
    allow_reuse_address = True

    # pylint: disable=C0103
    def __init__(self, addr, requestHandler=SimpleJSONRPCRequestHandler,
                 logRequests=True, encoding=None, bind_and_activate=True,
                 address_family=socket.AF_INET,
                 config=jsonrpclib.config.DEFAULT,
                 use_double_stack=False):
        """
        Sets up the server and the dispatcher

        :param addr: The server listening address
        :param requestHandler: Custom request handler
        :param logRequests: Flag to(de)activate requests logging
        :param encoding: The dispatcher request encoding
        :param bind_and_activate: If True, starts the server immediately
        :param address_family: The server listening address family
        :param config: A JSONRPClib Config instance
        :param use_double_stack: If True and in IPv6 mode, accept both IPv4
                                 and IPv6 clients
        """
        # Set up the dispatcher
        JsonRpcProtocolHandler.__init__(self, config)

        # Flag to ease handling of Unix socket mode
        unix_socket = address_family == _AF_UNIX

        # Disable the reuse address flag when in Unix socket mode, or an
        # exception will raise when binding the socket
        self.allow_reuse_address = self.allow_reuse_address and not unix_socket

        # Prepare the server configuration
        self.address_family = address_family
        self.json_config = config

        # logRequests is used by SimpleXMLRPCRequestHandler
        # This must be disabled in Unix socket mode (or an exception will raise
        # at each connection)
        self.logRequests = logRequests and not unix_socket

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

                if unix_socket:
                    # Disable TCP features over Unix socket, or an
                    # "invalid argument" error will raise
                    self.disable_nagle_algorithm = False

                super(RequestHandlerWrapper, self).__init__(*args, **kwargs)

        # Set up the server. Don't bind it yet if using double stack
        socketserver.TCPServer.__init__(
            self, addr, RequestHandlerWrapper,
            bind_and_activate and not use_double_stack
        )

        # Activate double stack
        if use_double_stack and address_family == socket.AF_INET6:
            ipv6utils.set_double_stack(self.socket, True)

            # Now we can activate the server
            if bind_and_activate:
                try:
                    self.server_bind()
                    self.server_activate()
                except:
                    self.server_close()
                    raise

        # Windows-specific
        if fcntl is not None and hasattr(fcntl, 'FD_CLOEXEC'):
            flags = fcntl.fcntl(self.fileno(), fcntl.F_GETFD)
            flags |= fcntl.FD_CLOEXEC
            fcntl.fcntl(self.fileno(), fcntl.F_SETFD, flags)

# ------------------------------------------------------------------------------


class PooledJSONRPCServer(SimpleJSONRPCServer, socketserver.ThreadingMixIn):
    """
    JSON-RPC server based on a thread pool
    """
    def __init__(self, addr, requestHandler=SimpleJSONRPCRequestHandler,
                 logRequests=True, encoding=None, bind_and_activate=True,
                 address_family=socket.AF_INET,
                 config=jsonrpclib.config.DEFAULT, thread_pool=None):
        """
        Sets up the server and the dispatcher

        :param addr: The server listening address
        :param requestHandler: Custom request handler
        :param logRequests: Flag to(de)activate requests logging
        :param encoding: The dispatcher request encoding
        :param bind_and_activate: If True, starts the server immediately
        :param address_family: The server listening address family
        :param config: A JSONRPClib Config instance
        :param thread_pool: A ThreadPool object. The pool must be started.
        """
        # Normalize the thread pool
        if thread_pool is None:
            # Start a thread pool with  30 threads max, 0 thread min
            thread_pool = jsonrpclib.threadpool.ThreadPool(
                30, 0, logname="PooledJSONRPCServer")
            thread_pool.start()

        # Store the thread pool
        self.__request_pool = thread_pool

        # Prepare the server
        SimpleJSONRPCServer.__init__(self, addr, requestHandler, logRequests,
                                     encoding, bind_and_activate,
                                     address_family, config)

    def process_request(self, request, client_address):
        """
        Handle a client request: queue it in the thread pool
        """
        self.__request_pool.enqueue(self.process_request_thread,
                                    request, client_address)

    def server_close(self):
        """
        Clean up the server
        """
        SimpleJSONRPCServer.shutdown(self)
        SimpleJSONRPCServer.server_close(self)
        self.__request_pool.stop()

# ------------------------------------------------------------------------------


class CGIJSONRPCRequestHandler(JsonRpcProtocolHandler, CGIXMLRPCRequestHandler):
    """
    JSON-RPC CGI handler (and dispatcher)
    """
    def __init__(self, encoding="UTF-8", config=jsonrpclib.config.DEFAULT):
        """
        Sets up the dispatcher

        :param encoding: Dispatcher encoding
        :param config: A JSONRPClib Config instance
        """
        JsonRpcProtocolHandler.__init__(self, config)
        CGIXMLRPCRequestHandler.__init__(self, encoding=encoding)

    def handle_jsonrpc(self, request_text):
        """
        Handle a JSON-RPC request
        """
        try:
            writer = sys.stdout.buffer
        except AttributeError:
            writer = sys.stdout

        response = self.marshaled_dispatch(request_text)
        response = response.encode(self.encoding)
        print("Content-Type:", self.json_config.content_type)
        print("Content-Length:", len(response))
        print()
        sys.stdout.flush()
        writer.write(response)
        writer.flush()

    # XML-RPC alias
    handle_xmlrpc = handle_jsonrpc
