#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
============================
JSONRPC Library (jsonrpclib)
============================

This library is a JSON-RPC v.2 (proposed) implementation which
follows the xmlrpclib API for portability between clients. It
uses the same Server / ServerProxy, loads, dumps, etc. syntax,
while providing features not present in XML-RPC like:

* Keyword arguments
* Notifications
* Versioning
* Batches and batch notifications

Eventually, I'll add a SimpleXMLRPCServer compatible library,
and other things to tie the thing off nicely. :)

For a quick-start, just open a console and type the following,
replacing the server address, method, and parameters
appropriately.
>>> import jsonrpclib
>>> server = jsonrpclib.Server('http://localhost:8181')
>>> server.add(5, 6)
11
>>> server._notify.add(5, 6)
>>> batch = jsonrpclib.MultiCall(server)
>>> batch.add(3, 50)
>>> batch.add(2, 3)
>>> batch._notify.add(3, 5)
>>> batch()
[53, 5]

See https://github.com/tcalmant/jsonrpclib for more info.

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

try:
    # Typing with mypy
    # pylint: disable=W0611
    from typing import Any, Callable, Dict, Generator, Iterator, List, Optional, \
        Tuple, Type, Union
    from ssl import SSLContext
    from jsonrpclib.impl import AbstractTransport
    import jsonrpclib.history
except ImportError:
    pass

# Standard library
import contextlib
import logging
import os
import socket

try:
    # Python 3
    # pylint: disable=F0401,E0611
    from http.client import HTTPConnection
    from urllib.parse import splittype, splithost
    from xmlrpc.client import Transport as XMLTransport
    from xmlrpc.client import SafeTransport as XMLSafeTransport
    from xmlrpc.client import ServerProxy as XMLServerProxy
    from xmlrpc.client import _Method as XML_Method
except ImportError:
    # Python 2
    # pylint: disable=F0401,E0611
    from httplib import HTTPConnection
    from urllib import splittype, splithost
    from xmlrpclib import Transport as XMLTransport
    from xmlrpclib import SafeTransport as XMLSafeTransport
    from xmlrpclib import ServerProxy as XMLServerProxy
    from xmlrpclib import _Method as XML_Method

try:
    # Check GZip support
    import gzip
except ImportError:
    # Python can be built without zlib/gzip support
    # pylint: disable=C0103
    gzip = None

# Library includes
from jsonrpclib.client_protocol import check_for_errors, dumps, loads
from jsonrpclib.exceptions import ProtocolError
from jsonrpclib.impl import AbstractTransport
import jsonrpclib.config
import jsonrpclib.utils as utils

# ------------------------------------------------------------------------------

# Module version
__version_info__ = (0, 4, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# Create the logger
_logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# XMLRPClib re-implementations


class JSONTarget(object):
    """
    Unmarshalls stream data to a string
    """

    def __init__(self):
        # type: () -> None
        """
        Sets up the unmarshaller
        """
        self.data = []  # type: Union[List[bytes], List[str]]

    def feed(self, data):
        # type: (Union[bytes, str]) -> None
        """
        Stores the given raw data into a buffer
        """
        # Store raw data as it might not contain whole wide-character
        self.data.append(data)

    def close(self):
        # type: () -> str
        """
        Unmarshalls the buffered data
        """
        if not self.data:
            return ''
        else:
            # Use type to have a valid join (str vs. bytes)
            data = type(self.data[0])().join(self.data)
            try:
                # Convert the whole final string
                data = utils.from_bytes(data)
            except:
                # Try a pass-through
                pass

            return data


class JSONParser(object):
    """
    Default JSON parser
    """

    def __init__(self, target):
        # type: (JSONTarget) -> None
        """
        Associates the target loader to the parser

        :param target: a JSONTarget instance
        """
        self.target = target

    def feed(self, data):
        # type: (bytes) -> None
        """
        Feeds the associated target with the given data
        """
        self.target.feed(data)

    @staticmethod
    def close():
        # type: () -> None
        """
        Does nothing
        """
        pass


class TransportMixIn(AbstractTransport):
    """ Just extends the XML-RPC transport where necessary. """
    # for Python 2.7 support
    _connection = None  # type: Optional[Tuple[str, HTTPConnection]]

    # List of non-overridable headers
    # Use the configuration to change the content-type
    readonly_headers = ('content-length', 'content-type')

    def __init__(self, config=jsonrpclib.config.DEFAULT, context=None):
        # type: (jsonrpclib.config.Config, Optional[SSLContext]) -> None
        """
        Sets up the transport

        :param config: A JSONRPClib Config instance
        """
        AbstractTransport.__init__(self)

        # Store the configuration
        self._config = config

        # Store the SSL context
        self.context = context

        # Set up the user agent
        self.user_agent = config.user_agent

        # Avoid a pep-8 error
        self.accept_gzip_encoding = True
        self.verbose = False

    def emit_additional_headers(self, connection):
        # type: (Any) -> Dict[str, Any]
        """
        Puts headers as is in the request, filtered read only headers

        :param connection: The request connection
        :return: The dictionary of headers added to the connection
        """
        # Setup extra headers
        # (list of tuples, inherited from xmlrpclib.client.Transport)
        # Authentication headers are stored there
        try:
            extra_headers = self._extra_headers
        except AttributeError:
            # Not available this version of Python (should not happen)
            extra_headers = []

        # Compute the headers
        additional_headers = self.compute_additional_headers(extra_headers)

        # Send them through the connection
        for key, value in additional_headers.items():
            connection.putheader(key, value)

        return additional_headers

    def single_request(self, host, handler, request_body, verbose=False):
        # type: (str, str, str, bool) -> Union[Dict[str, Any], List[Dict[str, Any]]]
        """
        Send a complete request, and parse the response.

        From xmlrpclib in Python 2.7

        :param host: Target host.
        :param handler: Target RPC handler.
        :param request_body: JSON-RPC request body.
        :param verbose: Debugging flag.
        :return: Parsed response.
        """
        connection = self.make_connection(host)  # type: HTTPConnection
        try:
            self.send_request(connection, handler, request_body, verbose)
            self.send_content(connection, request_body)

            response = connection.getresponse()
            if response.status == 200:
                self.verbose = verbose
                return self.parse_response(response)
        except:
            # All unexpected errors leave connection in
            # a strange state, so we clear it.
            self.close()
            raise

        # Discard any response data and raise exception
        if response.getheader("content-length", 0):
            response.read()
        raise ProtocolError(host + handler,
                            response.status, response.reason,
                            response.msg)

    def send_request(self, connection, handler, request_body, debug=False):
        # type: (Any, str, str, bool) -> HTTPConnection
        """
        Send HTTP request.

        From xmlrpc.client in Python 3.4

        :param connection: Connection handle.
        :param handler: Target RPC handler (a path relative to host)
        :param request_body: The JSON-RPC request body
        :param debug: Enable debugging if debug is true.
        :return: An HTTPConnection.
        """
        if debug:
            connection.set_debuglevel(1)
        if self.accept_gzip_encoding and gzip:
            connection.putrequest("POST", handler, skip_accept_encoding=True)
            connection.putheader("Accept-Encoding", "gzip")
        else:
            connection.putrequest("POST", handler)

        return connection

    def send_content(self, connection, request_body):
        # type: (Any, str) -> None
        """
        Completes the request headers and sends the request body of a JSON-RPC
        request over a HTTPConnection

        :param connection: An HTTPConnection object
        :param request_body: JSON-RPC request body
        """
        # Convert the body first
        request_body = utils.to_bytes(request_body)

        # "static" headers
        connection.putheader("Content-Type", self._config.content_type)
        connection.putheader("Content-Length", str(len(request_body)))

        # Emit additional headers here in order not to override content-length
        additional_headers = self.emit_additional_headers(connection)

        # Add the user agent, if not overridden
        if "user-agent" not in additional_headers:
            connection.putheader("User-Agent", self.user_agent)

        connection.endheaders()
        if request_body:
            connection.send(request_body)

    @staticmethod
    def getparser():
        # type: () -> Tuple[JSONParser, JSONTarget]
        """
        Create an instance of the parser, and attach it to an unmarshalling
        object. Return both objects.

        :return: The parser and unmarshaller instances
        """
        target = JSONTarget()
        return JSONParser(target), target


class Transport(TransportMixIn, XMLTransport):
    """
    Mixed-in HTTP transport
    """

    def __init__(self, config):
        # type: (jsonrpclib.config.Config) -> None
        """
        :param config: A jsonrpclib configuration
        """
        TransportMixIn.__init__(self, config)
        XMLTransport.__init__(self)


class SafeTransport(TransportMixIn, XMLSafeTransport):
    """
    Mixed-in HTTPS transport
    """

    def __init__(self, config, context):
        # type: (jsonrpclib.config.Config, Optional[SSLContext]) -> None
        """
        :param config: A jsonrpclib configuration
        :param context: An SSLContext object, if nay
        """
        TransportMixIn.__init__(self, config, context)
        try:
            # Give the context to XMLSafeTransport, to avoid it setting the
            # context to None.
            # See https://github.com/tcalmant/jsonrpclib/issues/39
            XMLSafeTransport.__init__(self, context=context)
        except TypeError:
            # On old versions of Python (Pre-2014), the context argument
            # wasn't available
            XMLSafeTransport.__init__(self)


# ------------------------------------------------------------------------------


class UnixHTTPConnection(HTTPConnection):
    """
    Replaces the connect() method of HTTPConnection to use a Unix socket
    """

    def __init__(self, path, *args, **kwargs):
        # type: (str, Any, Any) -> None
        """
        Constructs the HTTP connection.

        Forwards all given arguments except ``path`` to the constructor of
        HTTPConnection

        :param path: Path to the Unix socket
        """
        HTTPConnection.__init__(self, path, *args, **kwargs)
        self.path = path

    def connect(self):
        # type: () -> None
        """
        Connects to the described server
        """
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.path)


class UnixTransport(TransportMixIn, XMLTransport):
    """
    Mixed-in HTTP transport over a UNIX socket
    """

    def __init__(self, config, path=None):
        # type: (jsonrpclib.config.Config, Optional[str]) -> None
        """
        :param config: The jsonrpclib configuration
        :param path: Path to the Unix socket (overrides the host name later)
        """
        TransportMixIn.__init__(self, config)
        XMLTransport.__init__(self)
        # Keep track of the given path, if any
        self.__unix_path = os.path.abspath(path) if path else None

    def make_connection(self, host):
        # type: (str) -> HTTPConnection
        """
        Connect to server.

        Return an existing connection if possible.
        This allows HTTP/1.1 keep-alive.

        Code copied from xmlrpc.client (Python 3)

        :param host: Target host (ignored if a path was given)
        :return A UnixHTTPConnection object
        """
        if self.__unix_path:
            host = self.__unix_path

        if self._connection and host == self._connection[0]:
            return self._connection[1]

        # create a HTTP connection object from a host descriptor
        path, self._extra_headers, _ = self.get_host_info(host)
        self._connection = host, UnixHTTPConnection(path)
        return self._connection[1]


# ------------------------------------------------------------------------------


class ServerProxy(XMLServerProxy):
    """
    Unfortunately, much more of this class has to be copied since
    so much of it does the serialization.
    """

    def __init__(self, uri, transport=None, encoding=None,
                 verbose=0, version=None, headers=None, history=None,
                 config=jsonrpclib.config.DEFAULT, context=None):
        # type: (str, Optional[TransportMixIn], Optional[str], int, Any, Optional[List[Dict[str, Any]]], Optional[jsonrpclib.history.History], jsonrpclib.config.Config, Optional[SSLContext]) -> None
        """
        Sets up the server proxy

        :param uri: Request URI
        :param transport: Custom transport handler
        :param encoding: Specified encoding
        :param verbose: Log verbosity level
        :param version: JSON-RPC specification version
        :param headers: Custom additional headers for each request
        :param history: History object (for tests)
        :param config: A JSONRPClib Config instance
        :param context: The optional SSLContext to use
        """
        # Store the configuration
        self._config = config
        self.__version = version or config.version

        schema, uri = splittype(uri)
        use_unix = False
        if schema.startswith("unix+"):
            schema = schema[len("unix+"):]
            use_unix = True

        if schema not in ('http', 'https'):
            _logger.error("jsonrpclib only support http(s) URIs, not %s",
                          schema)
            raise IOError('Unsupported JSON-RPC protocol.')

        self.__host, self.__handler = splithost(uri)
        unix_path = None
        if use_unix:
            unix_path = self.__handler
            self.__handler = '/'
        elif not self.__handler:
            # Not sure if this is in the JSON spec?
            self.__handler = '/'

        if transport is None:
            if use_unix:
                if schema == "http":
                    # In Unix mode, we use the path part of the URL (handler)
                    # as the path to the socket file
                    transport = UnixTransport(
                        config=config, path=unix_path
                    )
            elif schema == 'https':
                transport = SafeTransport(config=config, context=context)
            else:
                transport = Transport(config=config)

            if transport is None:
                raise IOError(
                    "Unhandled combination: UNIX={}, protocol={}"
                        .format(use_unix, schema)
                )

        self.__transport = transport

        self.__encoding = encoding
        self.__verbose = verbose
        self.__history = history

        # Global custom headers are injected into Transport
        self.__transport.push_headers(headers or {})

    def __getattr__(self, name):
        # type: (str) -> _Method
        """
        Returns a callable object to call the remote service
        """
        if name.startswith("__") and name.endswith("__"):
            # Don't proxy special methods.
            raise AttributeError("ServerProxy has no attribute '%s'" % name)
        # Same as original, just with new _Method reference
        return _Method(self._request, name)

    def __call__(self, attr):
        # type: (str) -> Any
        """
        A workaround to get special attributes on the ServerProxy
        without interfering with the magic __getattr__

        (code from xmlrpclib in Python 2.7)
        """
        if attr == "close":
            return self.__close
        elif attr == "transport":
            return self.__transport

        raise AttributeError("Attribute {0} not found".format(attr))

    @property
    def _notify(self):
        # type: () -> _Notify
        """
        Like __getattr__, but sending a notification request instead of a call
        """
        return _Notify(self._request_notify)

    def __close(self):
        # type: () -> None
        """
        Closes the transport layer
        """
        self.__transport.close()

    def _request(self, methodname, params, rpcid=None):
        # type: (str, Any, Optional[str]) -> Any
        """
        Calls a method on the remote server

        :param methodname: Name of the method to call
        :param params: Method parameters
        :param rpcid: ID of the remote call
        :return: The parsed result of the call
        """
        request = dumps(params, methodname, encoding=self.__encoding,
                        rpcid=rpcid, version=self.__version,
                        config=self._config)
        response = self._run_request(request)  # type: Dict[str, Any]
        check_for_errors(response)
        return response['result']

    def _request_notify(self, methodname, params, rpcid=None):
        # type: (str, Any, Optional[str]) -> None
        """
        Calls a method as a notification

        :param methodname: Name of the method to call
        :param params: Method parameters
        :param rpcid: ID of the remote call
        """
        request = dumps(params, methodname, encoding=self.__encoding,
                        rpcid=rpcid, version=self.__version, notify=True,
                        config=self._config)
        response = self._run_request(request, notify=True)
        check_for_errors(response)

    def _run_request(self, request, notify=False):
        # type: (str, bool) -> Union[Any, Dict[str, Any], List[Dict[str, Any]]]
        """
        Sends the given request to the remote server

        :param request: The request to send
        :param notify: Notification request flag (unused)
        :return: The response as a parsed JSON object
        """
        if self.__history is not None:
            self.__history.add_request(request)

        response = self.__transport.request(
            self.__host,
            self.__handler,
            request,
            verbose=self.__verbose
        )

        # Here, the XMLRPC library translates a single list
        # response to the single value -- should we do the
        # same, and require a tuple / list to be passed to
        # the response object, or expect the Server to be
        # outputting the response appropriately?

        if self.__history is not None:
            self.__history.add_response(response)

        if not response:
            return None
        else:
            return_obj = loads(response, self._config)
            return return_obj

    @contextlib.contextmanager
    def _additional_headers(self, headers):
        # type: (Dict[str, Any]) -> Generator[ServerProxy, None, None]
        """
        Allows to specify additional headers, to be added inside the with
        block.
        Example of usage:

        >>> with client._additional_headers({'X-Test' : 'Test'}) as new_client:
        ...     new_client.method()
        ...
        >>> # Here old headers are restored
        """
        self.__transport.push_headers(headers)
        yield self
        self.__transport.pop_headers(headers)


# ------------------------------------------------------------------------------


class _Method(XML_Method):
    """
    Some magic to bind an JSON-RPC method to an RPC server.
    """

    def __call__(self, *args, **kwargs):
        """
        Sends an RPC request and returns the unmarshalled result
        """
        if args and kwargs:
            raise ProtocolError("Cannot use both positional and keyword "
                                "arguments (according to JSON-RPC spec.)")
        if args:
            return self.__send(self.__name, args)
        else:
            return self.__send(self.__name, kwargs)

    def __getattr__(self, name):
        """
        Returns a Method object for nested calls
        """
        if name == "__name__":
            return self.__name
        return _Method(self.__send, "{0}.{1}".format(self.__name, name))

    def __repr__(self):
        """
        Returns a string representation of the method
        """
        # Must use __class__ here because the base class is old-style.
        return "<{0} {1}>".format(self.__class__, self.__name)


class _Notify(object):
    """
    Same as _Method, but to send notifications
    """

    def __init__(self, request):
        # type: (Callable) -> None
        """
        Sets the method to call to send a request to the server
        """
        self._request = request

    def __getattr__(self, name):
        # type: (str) -> _Method
        """
        Returns a Method object, to be called as a notification
        """
        return _Method(self._request, name)


# ------------------------------------------------------------------------------
# Batch implementation


class MultiCallMethod(object):
    """
    Stores calls made to a MultiCall object for batch execution
    """

    def __init__(self, method, notify=False, config=jsonrpclib.config.DEFAULT):
        # type: (str, bool, jsonrpclib.config.Config) -> None
        """
        Sets up the store

        :param method: Name of the method to call
        :param notify: Notification flag
        :param config: Request configuration
        """
        self.method = method
        self.params = []  # type: Any
        self.notify = notify
        self._config = config

    def __repr__(self):
        """
        String representation
        """
        return str(self.request())

    def __getattr__(self, method):
        # type: (str) -> MultiCallMethod
        """
        Updates the object for a nested call
        """
        self.method = "{0}.{1}".format(self.method, method)
        return self

    def __call__(self, *args, **kwargs):
        # type: (Any, Any) -> None
        """
        Normalizes call parameters
        """
        if kwargs and args:
            raise ProtocolError('JSON-RPC does not support both ' +
                                'positional and keyword arguments.')
        if kwargs:
            self.params = kwargs
        else:
            self.params = args

    def request(self, encoding=None, rpcid=None):
        # type: (Optional[str], Optional[str]) -> str
        """
        Returns the request object as JSON-formatted string
        """
        return dumps(self.params, self.method, version=2.0,
                     encoding=encoding, rpcid=rpcid, notify=self.notify,
                     config=self._config)


class MultiCallNotify(object):
    """
    Same as MultiCallMethod but for notifications
    """

    def __init__(self, multicall, config=jsonrpclib.config.DEFAULT):
        # type: (MultiCall, jsonrpclib.config.Config) -> None
        """
        Sets ip the store

        :param multicall: The parent MultiCall instance
        :param config: Request configuration
        """
        self.multicall = multicall
        self._config = config

    def __getattr__(self, name):
        # type: (str) -> MultiCallMethod
        """
        Returns the MultiCallMethod to use as a notification
        """
        new_job = MultiCallMethod(name, notify=True, config=self._config)
        self.multicall._job_list.append(new_job)
        return new_job


class MultiCallIterator(object):
    """
    Iterates over the results of a MultiCall.
    Exceptions are raised in response to JSON-RPC faults
    """

    def __init__(self, results):
        # type: (List[Dict[str, Any]]) -> None
        """
        Sets up the results store
        """
        self.results = results

    @staticmethod
    def __get_result(item):
        # type: (Dict[str, Any]) -> Any
        """
        Checks for error and returns the "real" result stored in a MultiCall
        result.
        """
        check_for_errors(item)
        return item['result']

    def __iter__(self):
        # type: () -> Iterator[Any]
        """
        Iterates over all results
        """
        for item in self.results:
            yield self.__get_result(item)

        # Since Python 3.7, we must return instead of raising a StopIteration
        # (see PEP-479)
        return

    def __getitem__(self, i):
        # type: (int) -> Any
        """
        Returns the i-th object of the results
        """
        return self.__get_result(self.results[i])

    def __len__(self):
        """
        Returns the number of results stored
        """
        return len(self.results)


class MultiCall(object):
    """
    server -> a object used to boxcar method calls, where server should be a
    ServerProxy object.

    Methods can be added to the MultiCall using normal
    method call syntax e.g.:

    multicall = MultiCall(server_proxy)
    multicall.add(2,3)
    multicall.get_address("Guido")

    To execute the multicall, call the MultiCall object e.g.:

    add_result, address = multicall()
    """

    def __init__(self, server, config=jsonrpclib.config.DEFAULT):
        # type: (ServerProxy, jsonrpclib.config.Config) -> None
        """
        Sets up the multicall

        :param server: A ServerProxy object
        :param config: Request configuration
        """
        self._server = server
        self._job_list = []  # type: List[MultiCallMethod]
        self._config = config

    def _request(self):
        # type: () -> Optional[MultiCallIterator]
        """
        Sends the request to the server and returns the responses

        :return: A MultiCallIterator object
        """
        if len(self._job_list) < 1:
            # Should we alert? This /is/ pretty obvious.
            return None

        request_body = "[ {0} ]".format(
            ','.join(job.request() for job in self._job_list))
        responses = self._server._run_request(request_body)
        del self._job_list[:]

        return MultiCallIterator(responses or [])

    @property
    def _notify(self):
        # type: () -> MultiCallNotify
        """
        Prepares a notification call
        """
        return MultiCallNotify(self, self._config)

    def __getattr__(self, name):
        # type: (str) -> MultiCallMethod
        """
        Registers a method call
        """
        new_job = MultiCallMethod(name, config=self._config)
        self._job_list.append(new_job)
        return new_job

    __call__ = _request


# These lines conform to xmlrpclib's "compatibility" line.
# Not really sure if we should include these, but oh well.
Server = ServerProxy
