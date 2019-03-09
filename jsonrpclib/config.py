#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
The configuration module.

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
    from typing import Any, Callable, Dict, Optional, Type, Union
    from ssl import SSLContext
    from jsonrpclib.impl import AbstractTransport
    import jsonrpclib.history
except ImportError:
    pass

import sys

# ------------------------------------------------------------------------------

# Module version
__version_info__ = (0, 5, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------


class LocalClasses(dict):
    """
    Associates local classes with their names (used in the jsonclass module)
    """

    def add(self, cls, name=None):
        # type: (Type, Optional[str]) -> None
        """
        Stores a local class

        :param cls: A class
        :param name: Custom name used in the __jsonclass__ attribute
        """
        self[name or cls.__name__] = cls

    def copy(self):
        # type: () -> "LocalClasses"
        """
        Copies the current associations

        :return: A copy of this object
        """
        new_obj = LocalClasses()
        for key, value in self.items():
            new_obj[key] = value
        return new_obj


# ------------------------------------------------------------------------------


class Config(object):
    """
    This is pretty much used exclusively for the 'jsonclass'
    functionality... set use_jsonclass to False to turn it off.
    You can change serialize_method and ignore_attribute, or use
    the local_classes.add(class) to include "local" classes.
    """

    def __init__(
        self,
        version=2.0,
        content_type="application/json-rpc",
        user_agent=None,
        use_jsonclass=True,
        serialize_method="_serialize",
        ignore_attribute="_ignore",
        serialize_handlers=None,
    ):
        # type: (Union[str, float], str, Optional[str], bool, str, str, Optional[Dict[Type, Callable]]) -> None
        """
        Sets up a configuration of JSONRPClib

        :param version: JSON-RPC specification version
        :param content_type: HTTP content type header value
        :param user_agent: The HTTP request user agent
        :param use_jsonclass: Allow bean marshalling
        :param serialize_method: A string that references the method on a
                                 custom class object which is responsible for
                                 returning a tuple of the arguments and a dict
                                 of attributes.
        :param ignore_attribute: A string that references the attribute on a
                                 custom class object which holds strings and/or
                                 references of the attributes the class
                                 translator should ignore.
        :param serialize_handlers: A dictionary of dump handler functions by
                                   type for additional type support and for
                                   overriding dump of built-in types in utils
        """
        # JSON-RPC specification
        self.version = version

        # Change to False to keep __jsonclass__ entries raw.
        self.use_jsonclass = use_jsonclass

        # it SHOULD be 'application/json-rpc'
        # but MAY be 'application/json' or 'application/jsonrequest'
        self.content_type = content_type

        # Default user agent
        if user_agent is None:
            user_agent = "jsonrpclib/{0} (Python {1})".format(
                __version__, ".".join(str(ver) for ver in sys.version_info[:3])
            )
        self.user_agent = user_agent

        # The list of classes to use for jsonclass translation.
        self.classes = LocalClasses()

        # The serialize_method should be a string that references the
        # method on a custom class object which is responsible for
        # returning a tuple of the constructor arguments and a dict of
        # attributes.
        self.serialize_method = serialize_method

        # The ignore attribute should be a string that references the
        # attribute on a custom class object which holds strings and / or
        # references of the attributes the class translator should ignore.
        self.ignore_attribute = ignore_attribute

        # The list of serialize handler functions for jsonclass dump.
        # Used for handling additional types and overriding built-in types.
        # Functions are expected to have the same parameters as jsonclass dump
        # (possibility to call standard jsonclass dump function within).
        self.serialize_handlers = serialize_handlers or {}

    def copy(self):
        # type: () -> "Config"
        """
        Returns a shallow copy of this configuration bean

        :return: A shallow copy of this configuration
        """
        new_config = Config(
            self.version,
            self.content_type,
            self.user_agent,
            self.use_jsonclass,
            self.serialize_method,
            self.ignore_attribute,
            None,
        )
        new_config.classes = self.classes.copy()
        new_config.serialize_handlers = self.serialize_handlers.copy()
        return new_config


# Default configuration
DEFAULT = Config()
