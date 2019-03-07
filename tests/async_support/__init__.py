#!/usr/bin/env python
# -- Content-Encoding: UTF-8 --
"""
Test package for the asynchronous client & server implementations.

Only works with Python 3.5+

:license: Apache License 2.0
"""

import sys
import unittest

# Version check
if sys.version_info < (3, 5, 3):
    raise unittest.SkipTest("Python 3.5.3+ is required to run those tests")

# Import check
try:
    import aiohttp
except ImportError:
    raise unittest.SkipTest("async tests require aiohttp")
