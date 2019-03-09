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
    from typing import Any, Dict, List, Optional, Tuple
    from ssl import SSLContext
    import jsonrpclib.history
except ImportError:
    pass

# ------------------------------------------------------------------------------

# Module version
__version_info__ = (0, 5, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"


# ------------------------------------------------------------------------------


class AbstractTransport:
    """
    Abstract class for transport implementations
    """

    # List of non-overridable headers
    # Use the configuration to change the content-type
    readonly_headers = ("content-length", "content-type")

    def __init__(self):
        # type: () -> None
        # Additional headers: list of dictionaries
        self.additional_headers = []  # type: List[Dict[str, Any]]

    def close(self):
        # type: () -> None
        """
        Does nothing (API compliance)
        """

    def push_headers(self, headers):
        # type: (Dict[str, Any]) -> None
        """
        Adds a dictionary of headers to the additional headers list

        :param headers: A dictionary
        """
        self.additional_headers.append(headers)

    def pop_headers(self, headers):
        # type: (Dict[str, Any]) -> None
        """
        Removes the given dictionary from the additional headers list.
        Also validates that given headers are on top of the stack

        :param headers: Headers to remove
        :raise AssertionError: The given dictionary is not on the latest stored
                               in the additional headers list
        """
        assert self.additional_headers[-1] == headers
        self.additional_headers.pop()

    def compute_additional_headers(self, extra_headers=None):
        # type: (Optional[List[Tuple[str, Any]]]) -> Dict[str, Any]
        """
        Computes the headers to add to the request. Filters read only headers

        :return: The dictionary of headers added to the request
        """
        additional_headers = {}  # type: Dict[str, Any]

        # Add extra headers
        # (list of tuples, inherited from xmlrpclib.client.Transport)
        # Authentication headers are stored there
        if extra_headers:
            for key, value in extra_headers:
                additional_headers[key] = value

        # Prepare the merged dictionary
        for headers in self.additional_headers:
            additional_headers.update(headers)

        # Normalize keys and values
        additional_headers = {
            str(key).lower(): str(value)
            for key, value in additional_headers.items()
        }

        # Remove forbidden keys
        for forbidden in self.readonly_headers:
            additional_headers.pop(forbidden, None)

        return additional_headers
