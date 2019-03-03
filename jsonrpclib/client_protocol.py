#!/usr/bin/env python
# -- Content-Encoding: UTF-8 --
"""
Implementation of the JSON-RPC client-side protocol

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
    from typing import Any, Dict, List, Optional, Union
except ImportError:
    pass

# Standard library
import logging
import uuid

# Library includes
from jsonrpclib.exceptions import ProtocolError, AppError
from jsonrpclib.parser import jdumps, jloads
import jsonrpclib.config
import jsonrpclib.jsonclass as jsonclass
import jsonrpclib.utils as utils

# ------------------------------------------------------------------------------

# Module version
__version_info__ = (0, 5, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# Create the logger
_logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# JSON-RPC dump/load methods


def dump(
    params=None,
    methodname=None,
    rpcid=None,
    version=None,
    is_response=False,
    is_notify=False,
    config=jsonrpclib.config.DEFAULT,
):
    # type: (Optional[Union[Fault, List[Any]]], Optional[str], Optional[str], Union[str, float, None], bool, bool, jsonrpclib.config.Config) -> Dict[str, Any]
    """
    Prepares a JSON-RPC dictionary (request, notification, response or error)

    :param params: Method parameters (if a method name is given) or a Fault
    :param methodname: Method name
    :param rpcid: Request ID
    :param version: JSON-RPC version
    :param is_response: If True, this is a response dictionary
    :param is_notify: If True, this is a notification request
    :param config: A JSONRPClib Config instance
    :return: A JSON-RPC dictionary
    """
    # Default version
    if not version:
        version = config.version

    if not is_response and params is None:
        params = []

    # Validate method name and parameters
    valid_params = [utils.TupleType, utils.ListType, utils.DictType, Fault]
    if is_response:
        valid_params.append(type(None))

    if isinstance(methodname, utils.STRING_TYPES) and not isinstance(
        params, tuple(valid_params)
    ):
        """
        If a method, and params are not in a list-ish or a Fault,
        error out.
        """
        raise TypeError("Params must be a dict, list, tuple or Fault instance.")

    # Prepares the JSON-RPC content
    payload = Payload(rpcid=rpcid, version=version)

    if isinstance(params, Fault):
        # Prepare an error dictionary
        # pylint: disable=E1103
        return payload.error(params.faultCode, params.faultString, params.data)

    if not isinstance(methodname, utils.STRING_TYPES) and not is_response:
        # Neither a request nor a response
        raise ValueError(
            "Method name must be a string, or is_response "
            "must be set to True."
        )

    if config.use_jsonclass:
        # Use jsonclass to convert the parameters
        params = jsonclass.dump(params, config=config)

    if is_response:
        # Prepare a response dictionary
        if rpcid is None:
            # A response must have a request ID
            raise ValueError("A method response must have an rpcid.")
        return payload.response(params)

    if is_notify:
        # Prepare a notification dictionary
        return payload.notify(methodname, params)
    else:
        # Prepare a method call dictionary
        return payload.request(methodname, params)


def dumps(
    params=None,
    methodname=None,
    methodresponse=False,
    encoding=None,
    rpcid=None,
    version=None,
    notify=False,
    config=jsonrpclib.config.DEFAULT,
):
    # type: (Optional[Union[Fault, List[Any]]], Optional[str], bool, Optional[str], Optional[str], Union[str, float, None], bool, jsonrpclib.config.Config) -> str
    """
    Prepares a JSON-RPC request/response string

    :param params: Method parameters (if a method name is given) or a Fault
    :param methodname: Method name
    :param methodresponse: If True, this is a response dictionary
    :param encoding: Result string encoding
    :param rpcid: Request ID
    :param version: JSON-RPC version
    :param notify: If True, this is a notification request
    :param config: A JSONRPClib Config instance
    :return: A JSON-RPC dictionary
    """
    # Prepare the dictionary
    request = dump(
        params, methodname, rpcid, version, methodresponse, notify, config
    )

    # Returns it as a JSON string
    return jdumps(request, encoding=encoding or "UTF-8")


def load(data, config=jsonrpclib.config.DEFAULT):
    # type: (Optional[Dict[str, Any]], jsonrpclib.config.Config) -> Optional[Dict[str, Any]]
    """
    Loads a JSON-RPC request/response dictionary. Calls jsonclass to load beans

    :param data: A JSON-RPC dictionary
    :param config: A JSONRPClib Config instance (or None for default values)
    :return: A parsed dictionary or None
    """
    if data is None:
        # Notification
        return None

    # if the above raises an error, the implementing server code
    # should return something like the following:
    # { 'jsonrpc':'2.0', 'error': fault.error(), id: None }
    if config.use_jsonclass:
        # Convert beans
        data = jsonclass.load(data, config.classes)

    return data


def loads(data, config=jsonrpclib.config.DEFAULT):
    # type: (str, jsonrpclib.config.Config) -> Optional[Dict[str, Any]]
    """
    Loads a JSON-RPC request/response string. Calls jsonclass to load beans

    :param data: A JSON-RPC string
    :param config: A JSONRPClib Config instance (or None for default values)
    :return: A parsed dictionary or None
    :raise ValueError: Error parsing the JSON string
    """
    if not data:
        # Consider empty strings (or None) as notification results
        return None

    # Parse the JSON dictionary
    result = jloads(data)

    # Load the beans
    return load(result, config)

# ------------------------------------------------------------------------------
# Error and payload JSON representation classes


class Fault(object):
    """
    JSON-RPC error class
    """

    def __init__(
        self,
        code=-32000,
        message="Server error",
        rpcid=None,
        config=jsonrpclib.config.DEFAULT,
        data=None,
    ):
        # type: (int, str, Optional[str], jsonrpclib.config.Config, Any) -> None
        """
        Sets up the error description

        :param code: Fault code
        :param message: Associated message
        :param rpcid: Request ID
        :param config: A JSONRPClib Config instance
        :param data: Extra information added to an error description
        """
        self.faultCode = code
        self.faultString = message
        self.rpcid = rpcid
        self.config = config
        self.data = data

    def error(self):
        # type: () -> Dict[str, Any]
        """
        Returns the error as a dictionary

        :returns: A {'code', 'message'} dictionary
        """
        return {
            "code": self.faultCode,
            "message": self.faultString,
            "data": self.data,
        }

    def response(self, rpcid=None, version=None):
        # type: (Optional[str], Optional[float]) -> str
        """
        Returns the error as a JSON-RPC response string

        :param rpcid: Forced request ID
        :param version: JSON-RPC version
        :return: A JSON-RPC response string
        """
        if not version:
            version = self.config.version

        if rpcid:
            self.rpcid = rpcid

        return dumps(
            self,
            methodresponse=True,
            rpcid=self.rpcid,
            version=version,
            config=self.config,
        )

    def dump(self, rpcid=None, version=None):
        # type: (Optional[str], Optional[float]) -> Dict[str, Any]
        """
        Returns the error as a JSON-RPC response dictionary

        :param rpcid: Forced request ID
        :param version: JSON-RPC version
        :return: A JSON-RPC response dictionary
        """
        if not version:
            version = self.config.version

        if rpcid:
            self.rpcid = rpcid

        return dump(
            self,
            is_response=True,
            rpcid=self.rpcid,
            version=version,
            config=self.config,
        )

    def __repr__(self):
        """
        String representation
        """
        return "<Fault {0}: {1}>".format(self.faultCode, self.faultString)


class Payload(object):
    """
    JSON-RPC content handler
    """

    def __init__(
        self, rpcid=None, version=None, config=jsonrpclib.config.DEFAULT
    ):
        # type: (Optional[str], Any, jsonrpclib.config.Config) -> None
        """
        Sets up the JSON-RPC handler

        :param rpcid: Request ID
        :param version: JSON-RPC version
        :param config: A JSONRPClib Config instance
        """
        if not version:
            version = config.version

        self.id = rpcid
        self.version = float(version)

    def request(self, method, params=None):
        # type: (str, Any) -> Dict[str, Any]
        """
        Prepares a method call request

        :param method: Method name
        :param params: Method parameters
        :return: A JSON-RPC request dictionary
        :raise ValueError: Method name is not a string
        """
        if not isinstance(method, utils.STRING_TYPES):
            raise ValueError("Method name must be a string.")

        if not self.id:
            # Generate a request ID
            self.id = str(uuid.uuid4())

        request = {"id": self.id, "method": method}  # type: Dict[str, Any]
        if params or self.version < 1.1:
            request["params"] = params or []

        if self.version >= 2:
            request["jsonrpc"] = str(self.version)

        return request

    def notify(self, method, params=None):
        # type: (str, Any) -> Dict[str, Any]
        """
        Prepares a notification request

        :param method: Notification name
        :param params: Notification parameters
        :return: A JSON-RPC notification dictionary
        """
        # Prepare the request dictionary
        request = self.request(method, params)

        # Remove the request ID, as it's a notification
        if self.version >= 2:
            del request["id"]
        else:
            request["id"] = None

        return request

    def response(self, result=None):
        # type: (Any) -> Dict[str, Any]
        """
        Prepares a response dictionary

        :param result: The result of method call
        :return: A JSON-RPC response dictionary
        """
        response = {"result": result, "id": self.id}

        if self.version >= 2:
            response["jsonrpc"] = str(self.version)
        else:
            response["error"] = None

        return response

    def error(self, code=-32000, message="Server error.", data=None):
        # type: (int, str, Any) -> Dict[str, Any]
        """
        Prepares an error dictionary

        :param code: Error code
        :param message: Error message
        :param data: Extra data to associate to the error
        :return: A JSON-RPC error dictionary
        """
        error = self.response()
        if self.version >= 2:
            del error["result"]
        else:
            error["result"] = None
        error["error"] = {"code": code, "message": message}
        if data is not None:
            error["error"]["data"] = data
        return error


# ------------------------------------------------------------------------------
# Utility methods


def check_for_errors(result):
    # type: (Dict[str, Any]) -> Dict[str, Any]
    """
    Checks if a result dictionary signals an error

    :param result: A result dictionary
    :raise TypeError: Invalid parameter
    :raise NotImplementedError: Unknown JSON-RPC version
    :raise ValueError: Invalid dictionary content
    :raise ProtocolError: An error occurred on the server side
    :return: The result parameter
    """
    if not result:
        # Notification / empty result object
        return result

    if not isinstance(result, utils.DictType):
        # Invalid argument
        raise TypeError("Response is not a dict.")

    if "jsonrpc" in result and float(result["jsonrpc"]) > 2.0:
        # Unknown JSON-RPC version
        raise NotImplementedError("JSON-RPC version not yet supported.")

    if "result" not in result and "error" not in result:
        # Invalid dictionary content
        raise ValueError("Response does not have a result or error key.")

    if "error" in result and result["error"]:
        # Server-side error
        if "code" in result["error"]:
            # Code + Message
            code = result["error"]["code"]
            try:
                # Get the message (jsonrpclib)
                message = result["error"]["message"]
            except KeyError:
                # Get the trace (jabsorb)
                message = result["error"].get("trace", "<no error message>")

            if -32700 <= code <= -32000:
                # Pre-defined errors
                # See http://www.jsonrpc.org/specification#error_object
                raise ProtocolError((code, message))
            else:
                # Application error
                data = result["error"].get("data", None)
                raise AppError((code, message, data))
        elif isinstance(result["error"], dict) and len(result["error"]) == 1:
            # Error with a single entry ('reason', ...): use its content
            error_key = next(iter(result["error"].keys()))
            raise ProtocolError(result["error"][error_key])
        else:
            # Use the raw error content
            raise ProtocolError(result["error"])

    return result


def isbatch(request):
    # type: (Dict[str, Any]) -> bool
    """
    Tests if the given request is a batch call, i.e. a list of multiple calls

    :param request: a JSON-RPC request object
    :return: True if the request is a batch call
    """
    if not isinstance(request, (utils.ListType, utils.TupleType)):
        # Not a list: not a batch call
        return False
    elif len(request) < 1:
        # Only one request: not a batch call
        return False
    elif not isinstance(request[0], utils.DictType):
        # One of the requests is not a dictionary, i.e. a JSON Object
        # therefore it is not a valid JSON-RPC request
        return False
    elif "jsonrpc" not in request[0].keys():
        # No "jsonrpc" version in the JSON object: not a request
        return False

    try:
        version = float(request[0]["jsonrpc"])
    except ValueError:
        # Bad version of JSON-RPC
        raise ProtocolError('"jsonrpc" key must be a float(able) value.')

    if version < 2:
        # Batch call were not supported before JSON-RPC 2.0
        return False

    return True


def isnotification(request):
    # type: (Dict[str, Any]) -> bool
    """
    Tests if the given request is a notification

    :param request: A request dictionary
    :return: True if the request is a notification
    """
    try:
        # 1.0 notification if "id" is present but None
        return request["id"] is None
    except KeyError:
        # No "id" key in the request: 2.0 notification
        return True

    return False
