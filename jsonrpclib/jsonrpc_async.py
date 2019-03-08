#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Asynchronous version of the jsonrpclib client

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
    from typing import Any, Callable, Dict, List, Optional, Type
    from ssl import SSLContext
    from jsonrpclib.impl import AbstractAsyncTransport
    import jsonrpclib.history
except ImportError:
    pass

# Standard library
import contextlib
import logging

try:
    # Python 3
    # pylint: disable=F0401,E0611
    from urllib.parse import splittype, splithost
except ImportError:
    # Python 2
    # pylint: disable=F0401,E0611
    from urllib import splittype, splithost

# Library includes
from jsonrpclib.client_protocol import loads, dumps, check_for_errors
from jsonrpclib.exceptions import ProtocolError
import jsonrpclib.config

# ------------------------------------------------------------------------------

# Module version
__version_info__ = (0, 5, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# Create the logger
_logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------


class AsyncServerProxy:
    """
    Asynchronous version of the ServerProxy object
    """

    def __init__(
        self,
        uri,
        transport,
        encoding=None,
        verbose=False,
        version=None,
        headers=None,
        history=None,
        config=jsonrpclib.config.DEFAULT,
        context=None,
    ):
        # type: (str, Type[AbstractAsyncTransport], Optional[str], bool, Any, Optional[Dict[str, Any]], Optional[jsonrpclib.history.History], jsonrpclib.config.Config, Optional[SSLContext]) -> None
        """
        Sets up the server proxy

        :param uri: Request URI
        :param encoding: Specified encoding
        :param verbose: Log verbosity flag
        :param version: JSON-RPC specification version
        :param headers: Custom additional headers for each request
        :param history: History object (for tests)
        :param config: A JSONRPClib Config instance
        :param context: The optional SSLContext to use
        """
        # Store the configuration
        self._config = config
        self.__version = version or config.version
        self.__encoding = encoding
        self.__verbose = verbose
        self.__history = history

        # Check if we'll use TCP or Unix connector
        schema, uri = splittype(uri)
        use_unix = False
        if schema.startswith("unix+"):
            schema = schema[len("unix+"):]
            use_unix = True

        if schema not in ("http", "https"):
            _logger.error(
                "jsonrpclib only support http(s) URIs, not %s", schema
            )
            raise IOError("Unsupported JSON-RPC protocol.")

        # Keep track of the host and path parts
        self.__host, self.__handler = splithost(uri)
        unix_path = None
        if use_unix:
            unix_path = self.__handler
            self.__host = None
            self.__handler = "/"
        elif not self.__handler:
            # Not sure if this is in the JSON spec?
            self.__handler = "/"

        # aiohttp connector
        self.__transport = transport(
            schema, unix_path, context, self._config
        )

        # Global custom headers are injected into Transport
        self.__transport.push_headers(headers or {})

    def __getattr__(self, name):
        # type: (str) -> _AsyncMethod
        """
        Returns a callable object to call the remote service

        :return: A callable proxy object
        :raise AttributeError: Forbidden method name
        """
        if name.startswith("__") and name.endswith("__"):
            # Don't proxy special methods.
            raise AttributeError(
                "ServerProxy has no attribute '{}'".format(name)
            )

        # Same as original, just with new _Method reference
        return _AsyncMethod(self._request, name)

    @property
    def _notify(self):
        # type: () -> _AsyncNotify
        """
        Like __getattr__, but sending a notification request instead of a call
        """
        return _AsyncNotify(self._request_notify)

    def __call__(self, attr):
        # type: (str) -> Any
        """
        A workaround to get special attributes on the ``ServerProxy``
        without interfering with the magic ``__getattr__``

        (code from ``xmlrpclib`` in Python 2.7)

        :return: The special attribute matching the given name
        :raise AttributeError: Unknown special attribute
        """
        if attr == "close":
            return self.__close
        elif attr == "transport":
            return self.__transport

        raise AttributeError("Attribute {0} not found".format(attr))

    async def __close(self):
        # type: () -> None
        """
        Closes the transport layer
        """
        await self.__transport.close()

    async def _request(self, methodname, params, rpcid=None):
        # type: (str, Any, Optional[str]) -> Any
        """
        Calls a method on the remote server

        :param methodname: Name of the method to call
        :param params: Method parameters
        :param rpcid: ID of the remote call
        :return: The parsed result of the call
        """
        request = dumps(
            params,
            methodname,
            encoding=self.__encoding,
            rpcid=rpcid,
            version=self.__version,
            config=self._config,
        )
        response = await self._run_request(request)
        check_for_errors(response)
        if response is not None:
            return response["result"]
        return None

    async def _request_notify(self, methodname, params, rpcid=None):
        # type: (str, Any, Optional[str]) -> None
        """
        Calls a method as a notification

        :param methodname: Name of the method to call
        :param params: Method parameters
        :param rpcid: ID of the remote call
        """
        request = dumps(
            params,
            methodname,
            encoding=self.__encoding,
            rpcid=rpcid,
            version=self.__version,
            notify=True,
            config=self._config,
        )
        response = await self._run_request(request, notify=True)
        check_for_errors(response)

    async def _run_request(self, request, notify=False):
        # type: (str, bool) -> Optional[Dict[str, Any]]
        """
        Sends the given request to the remote server

        :param request: The request to send
        :param notify: Notification request flag (unused)
        :return: The response as a parsed JSON object
        """
        if self.__history is not None:
            self.__history.add_request(request)

        response = await self.__transport.request(
            self.__host, self.__handler, request, verbose=self.__verbose
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
# Proxy callables


class _AsyncMethod:
    """
    Some magic to bind an JSON-RPC method to an RPC server.
    """

    def __init__(self, send, name):
        # type: (Callable, str) -> None
        """
        :param send: The method to send the call request
        :param name: Name of the method
        """
        self.__send = send
        self.__name = name

    async def __call__(self, *args, **kwargs):
        """
        Sends an RPC request and returns the unmarshalled result
        """
        if args and kwargs:
            raise ProtocolError(
                "Cannot use both positional and keyword "
                "arguments (according to JSON-RPC spec.)"
            )
        if args:
            return await self.__send(self.__name, args)
        else:
            return await self.__send(self.__name, kwargs)

    def __getattr__(self, name):
        """
        Returns a Method object for nested calls
        """
        if name == "__name__":
            return self.__name
        return _AsyncMethod(self.__send, "{0}.{1}".format(self.__name, name))

    def __repr__(self):
        """
        Returns a string representation of the method
        """
        # Must use __class__ here because the base class is old-style.
        return "<{0} {1}>".format(self.__class__, self.__name)


class _AsyncNotify:
    """
    Same as ``_AsyncMethod``, but to send notifications
    """

    def __init__(self, request):
        # type: (Callable) -> None
        """
        Sets the method to call to send a request to the server
        """
        self._request = request

    def __getattr__(self, name):
        # type: (str) -> _AsyncMethod
        """
        Returns a Method object, to be called as a notification
        """
        return _AsyncMethod(self._request, name)
