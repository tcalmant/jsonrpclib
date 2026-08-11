#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Tests the dispatch hooks of SimpleJSONRPCDispatcher.

Both are public behaviours no other test covers: the custom dispatch method,
which replaces the resolution of the method names entirely (this is what Pelix
remote services rely on), and the notification thread pool.

:license: Apache License 2.0
"""

# Standard library
import json
import threading
import unittest

# JSON-RPC library
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCDispatcher
from jsonrpclib.threadpool import ThreadPool

# ------------------------------------------------------------------------------


def make_request(method, params=None, rpcid=1):
    """
    Prepares a JSON-RPC request string

    :param method: Name of the method to call
    :param params: Parameters of the call
    :param rpcid: Request ID (no ID at all if None, i.e. a notification)
    :return: The request, as a JSON string
    """
    request = {"jsonrpc": "2.0", "method": method, "params": params or []}
    if rpcid is not None:
        request["id"] = rpcid

    return json.dumps(request)


def registered(*args):
    """
    A method registered in the dispatcher
    """
    return "registered"


# ------------------------------------------------------------------------------


class DispatchMethodTests(unittest.TestCase):
    """
    Checks the custom dispatch method, which replaces the resolution of the
    method names (used by Pelix remote services)
    """

    def setUp(self):
        """
        Tests initialization
        """
        self.dispatcher = SimpleJSONRPCDispatcher()
        self.calls = []

    def dispatch(self, method, params):
        """
        Custom dispatch method: keeps track of the calls it gets

        :param method: Name of the method to call
        :param params: Parameters of the call
        :return: A constant result
        """
        self.calls.append((method, params))
        return "dispatched"

    def test_dispatch_method_resolves_unknown_names(self):
        """
        Tests that the custom dispatch method is called for a name the
        dispatcher knows nothing about
        """
        answer = json.loads(
            self.dispatcher._marshaled_dispatch(
                make_request("no.such.method", [1, 2]), self.dispatch
            )
        )

        self.assertEqual("dispatched", answer["result"])
        self.assertListEqual([("no.such.method", [1, 2])], self.calls)

    def test_dispatch_method_replaces_registered_methods(self):
        """
        Tests that the custom dispatch method has priority over the registered
        methods: it is the only resolution used
        """
        self.dispatcher.register_function(registered, "registered")

        answer = json.loads(
            self.dispatcher._marshaled_dispatch(
                make_request("registered"), self.dispatch
            )
        )

        self.assertEqual("dispatched", answer["result"])
        self.assertListEqual([("registered", [])], self.calls)

        # Without it, the registered method answers
        answer = json.loads(
            self.dispatcher._marshaled_dispatch(make_request("registered"))
        )
        self.assertEqual("registered", answer["result"])

    def test_dispatch_method_error(self):
        """
        Tests that an error raised by the custom dispatch method is reported
        as an internal error
        """

        def failing_dispatch(method, params):
            raise ValueError("No luck")

        answer = json.loads(
            self.dispatcher._marshaled_dispatch(
                make_request("whatever"), failing_dispatch
            )
        )

        self.assertEqual(-32603, answer["error"]["code"])
        self.assertNotIn("No luck", answer["error"]["message"])


# ------------------------------------------------------------------------------


class NotificationPoolTests(unittest.TestCase):
    """
    Checks the thread pool used to handle the notifications
    """

    def setUp(self):
        """
        Tests initialization
        """
        self.dispatcher = SimpleJSONRPCDispatcher()
        self.pool = ThreadPool(2, logname="test-notifications")
        self.pool.start()

        self.called = threading.Event()
        self.calls = []

    def tearDown(self):
        """
        Post-test clean up
        """
        self.dispatcher.set_notification_pool(None)
        self.pool.stop()

    def notified(self, *args):
        """
        Method called by the notifications
        """
        self.calls.append(args)
        self.called.set()

    def test_notification_without_pool(self):
        """
        Tests that a notification is handled in the calling thread when no
        pool is set, and that nothing is answered
        """
        self.dispatcher.register_function(self.notified, "notified")

        answer = self.dispatcher._marshaled_dispatch(
            make_request("notified", [1], rpcid=None)
        )

        self.assertEqual("", answer)
        self.assertListEqual([(1,)], self.calls)

    def test_notification_pool_is_used(self):
        """
        Tests that a notification is given to the pool, and that the answer is
        sent without waiting for it
        """
        self.dispatcher.register_function(self.notified, "notified")
        self.dispatcher.set_notification_pool(self.pool)

        answer = self.dispatcher._marshaled_dispatch(
            make_request("notified", [42], rpcid=None)
        )

        # No answer for a notification
        self.assertEqual("", answer)

        # The call is made by the pool
        self.assertTrue(self.called.wait(5), "The notification was not handled")
        self.assertListEqual([(42,)], self.calls)

    def test_notification_pool_with_dispatch_method(self):
        """
        Tests that a notification is given to the pool even when a custom
        dispatch method is used
        """
        self.dispatcher.set_notification_pool(self.pool)

        def dispatch(method, params):
            self.calls.append((method, params))
            self.called.set()

        answer = self.dispatcher._marshaled_dispatch(
            make_request("notified", [42], rpcid=None), dispatch
        )

        self.assertEqual("", answer)
        self.assertTrue(self.called.wait(5), "The notification was not handled")
        self.assertListEqual([("notified", [42])], self.calls)

    def test_call_is_not_given_to_the_pool(self):
        """
        Tests that a request with an ID is handled synchronously, even when a
        notification pool is set
        """
        self.dispatcher.register_function(registered, "registered")
        self.dispatcher.set_notification_pool(self.pool)

        answer = json.loads(
            self.dispatcher._marshaled_dispatch(make_request("registered"))
        )

        self.assertEqual("registered", answer["result"])


if __name__ == "__main__":
    unittest.main()
