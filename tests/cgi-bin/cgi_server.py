#!/usr/bin/env python
"""
Sample CGI server. Won't work with Python 3.15 and later
"""

import os
import sys

current_dir = os.path.dirname(__file__)
root_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, root_dir)

from jsonrpclib.SimpleJSONRPCServer import CGIJSONRPCRequestHandler  # noqa: E402


def add(a, b):
    return a + b


handler = CGIJSONRPCRequestHandler()
handler.register_function(add)
handler.handle_request()
