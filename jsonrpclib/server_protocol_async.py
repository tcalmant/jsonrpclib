#!/usr/bin/env python3
"""
Implementation of the JSON-RPC server-side protocol (async version)

This module requires Python 3.5+ to run.

:author: Thomas Calmant
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
    from typing import Any, Callable, Dict, List, Optional, Union, Coroutine
    from .server_protocol import ParamsList, DispatchMethod
except ImportError:
    pass

import inspect
import logging
import sys
import traceback

from jsonrpclib import Fault
from jsonrpclib.server_protocol import (
    JsonRpcProtocolHandler,
    NoMulticallResult,
    validate_request,
)
import jsonrpclib.config
import jsonrpclib.utils as utils

# ------------------------------------------------------------------------------

# Module-level logger
_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------


def ensure_async(function):
    # type: (Callable) -> Callable
    """
    Ensures that the given function can be used in an event loop

    :param function: Any callable
    :return: A coroutine
    """
    if inspect.iscoroutinefunction(function):
        return function

    async def async_func(*args, **kwargs):
        return function(*args, **kwargs)

    return async_func


class AsyncJsonRpcProtocolHandler(JsonRpcProtocolHandler):
    """
    Handling of the JSON-RPC protocol, without any dependency to third-party
    libraries

    This class inherits from the standard XML-RPC dispatcher only for its
    method registration handling.
    """

    def __init__(self, config=jsonrpclib.config.DEFAULT):
        # type: (jsonrpclib.config.Config) -> None
        """
        :param config: Configuration of the JSON-RPC server (version, ...)
        """
        # Call the constructor
        JsonRpcProtocolHandler.__init__(self, config)

        # Disable incompatible methods
        self.set_notification_pool = None
        self._marshaled_dispatch = None

    async def marshaled_dispatch(self, data, dispatch_method=None):
        # type: (str, Optional[DispatchMethod]) -> Optional[str]
        """
        Handle the JSON-RPC request (given as a string) and returns the
        JSON-RPC response as a string (asynchronous version)

        :param data: A JSON request string
        :param dispatch_method: Custom dispatch method (for method resolution)
        :return: A JSON-RPC response dictionary (or a list of) as a string
        """
        result = await self.handle_request_str(data, dispatch_method)
        if result is None:
            return None

        return jsonrpclib.jdumps(result)

    async def handle_request_str(self, json_str, dispatch_method=None):
        # type: (str, Optional[DispatchMethod]) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]
        """
        Parses the request string (marshaled), calls method(s) and returns a
        JSON-RPC dictionary (or a list of) (asynchronous version)

        :param json_str: A JSON request string
        :param dispatch_method: Custom dispatch method (for method resolution)
        :return: A JSON-RPC response dictionary (or a list of)
        """
        # Parse the request
        try:
            request = jsonrpclib.loads(json_str, self.json_config)
        except (ValueError, IOError, TypeError) as ex:
            # Parsing/loading error: return a JSON response
            fault = self.make_fault(
                -32700,
                "Request {0} invalid. ({1}:{2})".format(
                    json_str, type(ex).__name__, ex
                ),
            )
            return fault.dump()

        # Get the response dictionary
        try:
            # Return the response as is
            return await self.handle_request_dict(request, dispatch_method)
        except NoMulticallResult:
            # jsonrpclib internal behaviour: return nothing
            return None

    async def handle_request_dict(self, request, dispatch_method=None):
        # type: (Union[Dict[str, Any], List[Dict[str, Any]]], Optional[DispatchMethod]) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]
        """
        Loads the request dictionary (un-marshaled), calls the method(s)
        accordingly and returns a JSON-RPC dictionary
        (not marshaled, asynchronous version))

        :param request: JSON-RPC request dictionary (or list of)
        :param dispatch_method: Custom dispatch method (for method resolution)
        :return: A JSON-RPC dictionary (or an array of) or None if the request
                 was a notification
        :raise NoMulticallResult: No result in batch
        """
        if not request:
            # Invalid request dictionary
            fault = self.make_fault(
                -32600, "Request invalid -- no request data."
            )
            _logger.warning("Invalid request: %s", fault)
            return fault.dump()

        if isinstance(request, utils.ListType):
            # This SHOULD be a batch, by spec
            responses = []
            # TODO use gather to call methods in parallel
            for sub_req in request:
                response = await self._handle_single_call(
                    sub_req, dispatch_method
                )
                if response is not None:
                    responses.append(response)

            if not responses:
                # No non-None result
                _logger.error("No result in Multicall")
                raise NoMulticallResult("No result")

            return responses

        # Single call
        return await self._handle_single_call(request, dispatch_method)

    async def _handle_single_call(self, request, dispatch_method=None):
        # type: (Dict[str, Any], Optional[DispatchMethod]) -> Optional[Dict[str, Any]]
        """
        Calls the requested method returns a JSON-RPC dictionary
        (not marshaled, asynchronous version)

        :param request: JSON-RPC request dictionary
        :param dispatch_method: Custom dispatch method (for method resolution)
        :return: A JSON-RPC dictionary or None if the request was a notification
        """
        # Single call
        result = validate_request(request, self.json_config)
        if isinstance(result, Fault):
            return result.dump()

        # Call the method
        response = await self._dispatch_caller_single(request, dispatch_method)
        if isinstance(response, Fault):
            # pylint: disable=E1103
            return response.dump()

        return response

    async def _dispatch_caller_single(self, request, dispatch_method=None):
        # type: (Dict[str, Any], Optional[DispatchMethod]) -> Optional[Dict[str, Any]]
        """
        Dispatches a single method call (asynchronous version)

        :param request: A validated request dictionary
        :param dispatch_method: Custom dispatch method (for method resolution)
        :return: A JSON-RPC response dictionary, or None if it was a
                 notification request
        """
        method = request["method"]  # type: str
        params = request["params"]  # type: ParamsList

        # Prepare a request-specific configuration
        if "jsonrpc" not in request and self.json_config.version >= 2:
            # JSON-RPC 1.0 request on a JSON-RPC 2.0
            # => compatibility needed
            config = self.json_config.copy()
            config.version = 1.0
        else:
            # Keep server configuration as is
            config = self.json_config

        # Test if this is a notification request
        is_notification = "id" not in request or request["id"] in (None, "")
        # TODO try to act like in synchronous mode: return immediately and let
        # the notification work in background

        # Not a notification: we'll have to get a result
        try:
            # Call the method
            if dispatch_method is not None:
                response = await dispatch_method(method, params)
            else:
                response = await self._dispatch(method, params, config)
        except Exception as ex:
            # Return a fault
            fault = self.make_fault(
                -32603, "{0}:{1}".format(type(ex).__name__, ex), config=config
            )
            _logger.error("Error calling method %s: %s", method, fault)
            return fault.dump()

        if is_notification:
            # It's a notification, no result needed
            # Do not use 'not id' as it might be the integer 0
            return None

        # Prepare a JSON-RPC dictionary
        try:
            return jsonrpclib.dump(
                response, rpcid=request["id"], is_response=True, config=config
            )
        except Exception as ex:
            # JSON conversion exception
            fault = self.make_fault(
                -32603, "{0}:{1}".format(type(ex).__name__, ex), config=config
            )
            _logger.error("Error preparing JSON-RPC result: %s", fault)
            return fault.dump()

    async def _dispatch(self, method, params, config=None):
        # type: (str, ParamsList, Optional[jsonrpclib.config.Config]) -> Any
        """
        Default method resolver and caller (asynchronous version)

        :param method: Name of the method to call
        :param params: List of arguments to give to the method
        :param config: Request-specific configuration
        :return: The result of the method
        """
        config = config or self.json_config

        func = self._resolve_method(method, params)
        if func is not None:
            # Ensure we can wait for this coroutine
            func_async = ensure_async(func)

            try:
                # Call the method
                if isinstance(params, utils.ListType):
                    # Got a list of parameters
                    return await func_async(*params)

                # Got a dictionary of parameters
                return await func_async(**params)
            except TypeError as ex:
                # Maybe the parameters are wrong
                fault = self.make_fault(
                    -32602, "Invalid parameters: {0}".format(ex), config=config
                )
                _logger.warning("Invalid call parameters: %s", fault)
                return fault
            except:
                # Method exception
                err_lines = traceback.format_exception(*sys.exc_info())
                trace_string = "{0} | {1}".format(
                    err_lines[-2].splitlines()[0].strip(), err_lines[-1]
                )
                fault = self.make_fault(
                    -32603,
                    "Server error: {0}".format(trace_string),
                    config=config,
                )
                _logger.exception("Server-side exception: %s", fault)
                return fault

        # Unknown method
        fault = self.make_fault(
            -32601, "Method {0} not supported.".format(method), config=config
        )
        _logger.warning("Unknown method: %s", fault)
        return fault
