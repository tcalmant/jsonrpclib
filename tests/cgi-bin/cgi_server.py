#!/usr/bin/env python
"""
Sample CGI server
"""

import os
import sys

current_dir = os.path.dirname(__file__)
root_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, root_dir)

from jsonrpclib.SimpleJSONRPCServer import CGIJSONRPCRequestHandler


def add(a, b):
    return a + b


handler = CGIJSONRPCRequestHandler()
handler.register_function(add)
handler.handle_request()
