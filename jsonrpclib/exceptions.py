#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Definition of the types of exceptions

:authors: Josh Marshall, Thomas Calmant
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

# Module version
__version_info__ = (0, 5, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------


class ProtocolError(Exception):
    """
    JSON-RPC error

    ProtocolError.args[0] can be:
    * an error message (string)
    * a (code, message) tuple
    """


class AppError(ProtocolError):
    """
    Application error: the error code is not in the pre-defined ones

    AppError.args[0][0]: Error code
    AppError.args[0][1]: Error message or trace
    AppError.args[0][2]: Associated data
    """

    def data(self):
        """
        Retrieves the value found in the 'data' entry of the error, or None

        :return: The data associated to the error, or None
        """
        return self.args[0][2]
