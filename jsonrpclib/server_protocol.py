#!/usr/bin/env python
# -- Content-Encoding: UTF-8 --
"""
Implementation of the JSON-RPC server-side protocol

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
    from typing import Any, Callable, Dict, List, Optional, Union
    from jsonrpclib.threadpool import ThreadPool

    ParamsList = Union[List[Any], Dict[str, Any]]
    DispatchMethod = Callable[[str, ParamsList], Any]
except ImportError:
    pass

import logging
import sys
import traceback

try:
    # Python 3
    # pylint: disable=F0401,E0611
    import xmlrpc.server as xmlrpcserver
except (ImportError, AttributeError):
    # Python 2 or IronPython
    # pylint: disable=F0401,E0611
    import SimpleXMLRPCServer as xmlrpcserver

from jsonrpclib import Fault
import jsonrpclib.config
import jsonrpclib.utils as utils

# ------------------------------------------------------------------------------

# Module-level logger
_logger = logging.getLogger(__name__)

# Easy access to the method
resolve_dotted_attribute = xmlrpcserver.resolve_dotted_attribute

# ------------------------------------------------------------------------------


class NoMulticallResult(Exception):
    """
    No result in multicall
    """


def get_version(request):
    # type: (Dict[str, Any]) -> Optional[float]
    """
    Computes the JSON-RPC version

    :param request: A request dictionary
    :return: The JSON-RPC version or None
    """
    if "jsonrpc" in request:
        return 2.0

    if "id" in request:
        return 1.0

    return None


def validate_request(request, json_config):
    # type: (Dict[str, Any], jsonrpclib.config.Config) -> Union[bool, Fault]
    """
    Validates the format of a request dictionary

    :param request: A request dictionary
    :param json_config: A JSONRPClib Config instance
    :return: True if the dictionary is valid, else a Fault object
    """
    if not isinstance(request, utils.DictType):
        # Invalid request type
        fault = Fault(
            -32600,
            "Request must be a dict, not {0}".format(type(request).__name__),
            config=json_config,
        )
        _logger.warning("Invalid request content: %s", fault)
        return fault

    # Get the request ID
    rpcid = request.get("id", None)

    # Check request version
    version = get_version(request)
    if not version:
        fault = Fault(
            -32600,
            "Request {0} invalid.".format(request),
            rpcid=rpcid,
            config=json_config,
        )
        _logger.warning("No version in request: %s", fault)
        return fault

    # Default parameters: empty list
    request.setdefault("params", [])

    # Check parameters
    method = request.get("method", None)
    params = request.get("params")
    param_types = (utils.ListType, utils.DictType, utils.TupleType)

    if (
        not method
        or not isinstance(method, utils.STRING_TYPES)
        or not isinstance(params, param_types)
    ):
        # Invalid type of method name or parameters
        fault = Fault(
            -32600,
            "Invalid request parameters or method.",
            rpcid=rpcid,
            config=json_config,
        )
        _logger.warning("Invalid request content: %s", fault)
        return fault

    # Valid request
    return True


# ------------------------------------------------------------------------------


class JsonRpcProtocolHandler(xmlrpcserver.SimpleXMLRPCDispatcher, object):
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
        xmlrpcserver.SimpleXMLRPCDispatcher.__init__(self, allow_none=True)

        # Configuration of the protocol
        self.json_config = config

        # Notification thread pool
        self.__notification_pool = None  # type: Optional[ThreadPool]

    def set_notification_pool(self, thread_pool):
        # type: (Optional[ThreadPool]) -> None
        """
        Sets the thread pool to use to handle notifications
        """
        self.__notification_pool = thread_pool

    def make_fault(self, code, message, config=None):
        # type: (int, str, jsonrpclib.config.Config) -> Fault
        """
        Construct a Fault object, using the configuration of this protocol
        handler if no custom one is given

        :param code: Error code (should be negative)
        :param message: Message string
        :param config: Custom protocol configuration for the response
        :return: A Fault object
        """
        return Fault(code, message, config=config or self.json_config)

    def _marshaled_dispatch(self, data, dispatch_method=None, path=None):
        # type: (str, Optional[DispatchMethod], Optional[str]) -> Optional[str]
        """
        Overrides the XML-RPC dispatcher method. Calls marshaled_dispatch().

        :param data: A JSON request string
        :param dispatch_method: Custom dispatch method (for method resolution)
        :param path: Unused (exists in the overridden method).
        :return: A JSON-RPC response dictionary (or a list of) as a string
        """
        return self.marshaled_dispatch(data, dispatch_method)

    def marshaled_dispatch(self, data, dispatch_method=None):
        # type: (str, Optional[DispatchMethod]) -> Optional[str]
        """
        Handle the JSON-RPC request (given as a string) and returns the
        JSON-RPC response as a string.

        :param data: A JSON request string
        :param dispatch_method: Custom dispatch method (for method resolution)
        :return: A JSON-RPC response dictionary (or a list of) as a string
        """
        result = self.handle_request_str(data, dispatch_method)
        if result is None:
            return None

        return jsonrpclib.jdumps(result)

    def handle_request_str(self, json_str, dispatch_method=None):
        # type: (str, Optional[DispatchMethod]) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]
        """
        Parses the request string (marshaled), calls method(s) and returns a
        JSON-RPC dictionary (or a list of)

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
            return self.handle_request_dict(request, dispatch_method)
        except NoMulticallResult:
            # jsonrpclib internal behaviour: return nothing
            return None

    def handle_request_dict(self, request, dispatch_method=None):
        # type: (Union[Dict[str, Any], List[Dict[str, Any]]], Optional[DispatchMethod]) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]
        """
        Loads the request dictionary (un-marshaled), calls the method(s)
        accordingly and returns a JSON-RPC dictionary (not marshaled)

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
            for sub_req in request:
                response = self._handle_single_call(sub_req, dispatch_method)
                if response is not None:
                    responses.append(response)

            if not responses:
                # No non-None result
                _logger.error("No result in Multicall")
                raise NoMulticallResult("No result")

            return responses

        # Single call
        return self._handle_single_call(request, dispatch_method)

    def _handle_single_call(self, request, dispatch_method=None):
        # type: (Dict[str, Any], Optional[DispatchMethod]) -> Optional[Dict[str, Any]]
        """
        Calls the requested method returns a JSON-RPC dictionary (not marshaled)

        :param request: JSON-RPC request dictionary
        :param dispatch_method: Custom dispatch method (for method resolution)
        :return: A JSON-RPC dictionary or None if the request was a notification
        """
        # Single call
        result = validate_request(request, self.json_config)
        if isinstance(result, Fault):
            return result.dump()

        # Call the method
        response = self._dispatch_caller_single(request, dispatch_method)
        if isinstance(response, Fault):
            # pylint: disable=E1103
            return response.dump()

        return response

    def _dispatch_caller_single(self, request, dispatch_method=None):
        # type: (Dict[str, Any], Optional[DispatchMethod]) -> Optional[Dict[str, Any]]
        """
        Dispatches a single method call

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
        if is_notification and self.__notification_pool is not None:
            # Use the thread pool for notifications
            if dispatch_method is not None:
                self.__notification_pool.enqueue(
                    dispatch_method, method, params
                )
            else:
                self.__notification_pool.enqueue(
                    self._dispatch, method, params, config
                )

            # Return immediately
            return None

        # Not a notification: we'll have to get a result
        try:
            # Call the method
            if dispatch_method is not None:
                response = dispatch_method(method, params)
            else:
                response = self._dispatch(method, params, config)
        except Exception as ex:
            # Return a fault
            fault = Fault(
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
            fault = Fault(
                -32603, "{0}:{1}".format(type(ex).__name__, ex), config=config
            )
            _logger.error("Error preparing JSON-RPC result: %s", fault)
            return fault.dump()

    def _resolve_method(self, method, params):
        # type: (str, ParamsList) -> Optional[Callable]
        """
        Returns the method matching the given name

        :param method: A method name
        :param params: Parameters of the method (given to the sub-dispatcher)
        :return: The method to call or None
        """
        try:
            # Look into registered methods
            return self.funcs[method]
        except KeyError:
            if self.instance is not None:
                # Try with the registered instance
                try:
                    # Instance has a custom dispatcher
                    return getattr(self.instance, "_dispatch")(method, params)
                except AttributeError:
                    # Resolve the method name in the instance
                    try:
                        return resolve_dotted_attribute(
                            self.instance, method, True
                        )
                    except AttributeError:
                        # Unknown method
                        pass

        return None

    def _dispatch(self, method, params, config=None):
        # type: (str, ParamsList, Optional[jsonrpclib.config.Config]) -> Any
        """
        Default method resolver and caller

        :param method: Name of the method to call
        :param params: List of arguments to give to the method
        :param config: Request-specific configuration
        :return: The result of the method
        """
        config = config or self.json_config

        func = self._resolve_method(method, params)
        if func is not None:
            try:
                # Call the method
                if isinstance(params, utils.ListType):
                    # Got a list of parameters
                    return func(*params)

                # Got a dictionary of parameters
                return func(**params)
            except TypeError as ex:
                # Maybe the parameters are wrong
                fault = self.make_fault(
                    -32602, "Invalid parameters: {0}".format(ex), config
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
                    -32603, "Server error: {0}".format(trace_string), config
                )
                _logger.exception("Server-side exception: %s", fault)
                return fault

        # Unknown method
        fault = self.make_fault(
            -32601, "Method {0} not supported.".format(method), config
        )
        _logger.warning("Unknown method: %s", fault)
        return fault
