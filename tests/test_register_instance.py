#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Tests the resolution of method names on a registered instance.

Dotted names let a client walk the attributes of the registered instance, which
can reach any callable it holds a reference to: as in SimpleXMLRPCServer, this
must stay an explicit opt-in.

:license: Apache License 2.0
"""

# Standard library
import socket
import threading
import unittest

# JSON-RPC library
from jsonrpclib import ProtocolError, ServerProxy
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer

# ------------------------------------------------------------------------------

HOST = socket.gethostbyname("localhost")


class Nested(object):
    """
    An object the registered instance holds a reference to
    """

    def hello(self):
        """
        Method a client should not be able to reach by default
        """
        return "nested hello"


class Service(object):
    """
    A service registered with register_instance()
    """

    def __init__(self):
        """
        Sets up members
        """
        # A plain attribute holding another object: this is all the traversal
        # needs (a module here would give access to os.system & friends)
        self.nested = Nested()
        self._private = Nested()

    def ping(self):
        """
        A normal, directly registered method
        """
        return "pong"


# ------------------------------------------------------------------------------


class RegisterInstanceTests(unittest.TestCase):
    """
    Checks how method names are resolved on a registered instance
    """

    def setUp(self):
        """
        Tests initialization
        """
        self.server = None
        self.thread = None

    def tearDown(self):
        """
        Post-test clean up
        """
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(5)
            self.server = None
            self.thread = None

    def make_client(self, **kwargs):
        """
        Starts a server with a registered instance and returns a client for it

        :param kwargs: Arguments given to register_instance()
        :return: A ServerProxy talking to the server
        """
        self.server = SimpleJSONRPCServer((HOST, 0), logRequests=False)
        self.server.register_instance(Service(), **kwargs)

        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

        port = self.server.socket.getsockname()[1]
        return ServerProxy("http://{0}:{1}".format(HOST, port))

    def assert_refused(self, method):
        """
        Asserts that calling the given method is refused as unknown

        :param method: A bound remote method
        """
        try:
            method()
        except ProtocolError as ex:
            # Unknown method
            self.assertEqual(-32601, ex.args[0][0])
        else:
            self.fail("The method should not have been resolved")

    def test_dotted_names_refused_by_default(self):
        """
        Tests that register_instance() doesn't allow attribute traversal
        """
        client = self.make_client()

        # The methods of the instance itself are still reachable
        self.assertEqual("pong", client.ping())

        # ... but its attributes are not walked
        self.assert_refused(client.nested.hello)

    def test_dotted_names_opt_in(self):
        """
        Tests that attribute traversal is available when explicitly requested
        """
        client = self.make_client(allow_dotted_names=True)

        self.assertEqual("pong", client.ping())
        self.assertEqual("nested hello", client.nested.hello())

    def test_private_attributes_always_refused(self):
        """
        Tests that private attributes are refused, even when dotted names are
        allowed
        """
        for kwargs in ({}, {"allow_dotted_names": True}):
            client = self.make_client(**kwargs)
            try:
                self.assert_refused(client._private.hello)
            finally:
                self.tearDown()

    def test_unknown_method(self):
        """
        Tests that an unknown method is still reported as such
        """
        client = self.make_client()
        self.assert_refused(client.no_such_method)


if __name__ == "__main__":
    unittest.main()
