#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Tests JSON-RPC compatibility

:license: Apache License 2.0
"""

# Standard library
import json
import unittest

# Tests utilities
from tests.utilities import UtilityServer

# JSON-RPC library
import jsonrpclib
import jsonrpclib.config
from jsonrpclib.client_protocol import isbatch, isnotification

# ------------------------------------------------------------------------------


class TestCompatibility(unittest.TestCase):
    """
    Tests JSON-RPC compatibility
    """
    def setUp(self):
        """
        Pre-test set up
        """
        # Set up the server
        self.server = UtilityServer().start('', 0)
        self.port = self.server.get_port()

        # Set up the client
        self.history = jsonrpclib.history.History()
        self.client = jsonrpclib.ServerProxy(
            'http://localhost:{0}'.format(self.port), history=self.history)

    def tearDown(self):
        """
        Post-test clean up
        """
        # Close the client
        self.client("close")()

        # Stop the server
        self.server.stop()

    # Version 2.0 Tests
    def test_positional(self):
        """
        Positional arguments in a single call
        """
        result = self.client.subtract(23, 42)
        self.assertTrue(result == -19)
        result = self.client.subtract(42, 23)
        self.assertTrue(result == 19)
        request = json.loads(self.history.request)
        response = json.loads(self.history.response)
        verify_request = {
            "jsonrpc": "2.0", "method": "subtract",
            "params": [42, 23], "id": request['id']
        }
        verify_response = {
            "jsonrpc": "2.0", "result": 19, "id": request['id']
        }
        self.assertTrue(request == verify_request)
        self.assertTrue(response == verify_response)

    def test_named(self):
        """
        Named arguments in a single call
        """
        result = self.client.subtract(subtrahend=23, minuend=42)
        self.assertTrue(result == 19)
        result = self.client.subtract(minuend=42, subtrahend=23)
        self.assertTrue(result == 19)
        request = json.loads(self.history.request)
        response = json.loads(self.history.response)
        verify_request = {
            "jsonrpc": "2.0", "method": "subtract",
            "params": {"subtrahend": 23, "minuend": 42},
            "id": request['id']
        }
        verify_response = {
            "jsonrpc": "2.0", "result": 19, "id": request['id']
        }
        self.assertTrue(request == verify_request)
        self.assertTrue(response == verify_response)

    def test_notification(self):
        """ Testing a notification (response should be null) """
        result = self.client._notify.update(1, 2, 3, 4, 5)
        self.assertTrue(result is None)
        request = json.loads(self.history.request)
        response = self.history.response
        verify_request = {
            "jsonrpc": "2.0", "method": "update", "params": [1, 2, 3, 4, 5]
        }
        verify_response = ''
        self.assertTrue(request == verify_request)
        self.assertTrue(response == verify_response)

    def test_non_existent_method(self):
        """
        Tests error response for non-existent response
        """
        self.assertRaises(jsonrpclib.ProtocolError, self.client.foobar)
        request = json.loads(self.history.request)
        response = json.loads(self.history.response)
        verify_request = {
            "jsonrpc": "2.0", "method": "foobar", "id": request['id']
        }
        verify_response = {
            "jsonrpc": "2.0",
            "error":
                {"code": -32601, "message": response['error']['message']},
            "id": request['id']
        }
        self.assertTrue(request == verify_request)
        self.assertTrue(response == verify_response)

    def test_special_method(self):
        """
        Tests the access to a special method
        """
        self.assertRaises(AttributeError, getattr, self.client, "__special_method__")
        self.assertIsNone(self.history.request)

    def test_invalid_json(self):
        """
        Tests an invalid JSON request
        """
        invalid_json = '{"jsonrpc": "2.0", "method": "foobar, ' + \
            '"params": "bar", "baz]'
        self.client._run_request(invalid_json)
        response = json.loads(self.history.response)
        verify_response = json.loads(
            '{"jsonrpc": "2.0", "error": {"code": -32700,' +
            ' "message": "Parse error."}, "id": null}'
        )
        verify_response['error']['message'] = response['error']['message']
        self.assertTrue(response == verify_response)

    def test_invalid_request(self):
        """
        Tests an invalid "params" entry
        """
        invalid_request = '{"jsonrpc": "2.0", "method": 1, "params": "bar"}'
        self.client._run_request(invalid_request)
        response = json.loads(self.history.response)
        verify_response = json.loads(
            '{"jsonrpc": "2.0", "error": {"code": -32600, ' +
            '"message": "Invalid Request."}, "id": null}'
        )
        verify_response['error']['message'] = response['error']['message']
        self.assertTrue(response == verify_response)

    def test_batch_invalid_json(self):
        """
        Tests an invalid JSON batch request
        """
        invalid_request = '[ {"jsonrpc": "2.0", "method": "sum", ' + \
            '"params": [1,2,4], "id": "1"},{"jsonrpc": "2.0", "method" ]'
        self.client._run_request(invalid_request)
        response = json.loads(self.history.response)
        verify_response = json.loads(
            '{"jsonrpc": "2.0", "error": {"code": -32700,' +
            '"message": "Parse error."}, "id": null}'
        )
        verify_response['error']['message'] = response['error']['message']
        self.assertTrue(response == verify_response)

    def test_empty_array(self):
        """
        Tests an empty JSON array request
        """
        invalid_request = '[]'
        self.client._run_request(invalid_request)
        response = json.loads(self.history.response)
        verify_response = json.loads(
            '{"jsonrpc": "2.0", "error": {"code": -32600, ' +
            '"message": "Invalid Request."}, "id": null}'
        )
        verify_response['error']['message'] = response['error']['message']
        self.assertTrue(response == verify_response)

    def test_nonempty_array(self):
        """
        Tests an invalid JSON array request
        """
        invalid_request = '[1,2]'
        request_obj = json.loads(invalid_request)
        self.client._run_request(invalid_request)
        response = json.loads(self.history.response)
        self.assertTrue(len(response) == len(request_obj))
        for resp in response:
            verify_resp = json.loads(
                '{"jsonrpc": "2.0", "error": {"code": -32600, ' +
                '"message": "Invalid Request."}, "id": null}'
            )
            verify_resp['error']['message'] = resp['error']['message']
            self.assertTrue(resp == verify_resp)

    def test_batch(self):
        """
        Tests a mixed batch call
        """
        multicall = jsonrpclib.MultiCall(self.client)
        multicall.sum(1, 2, 4)
        multicall._notify.notify_hello(7)
        multicall.subtract(42, 23)
        multicall.foo.get(name='myself')
        multicall.get_data()
        job_requests = [j.request() for j in multicall._job_list]
        job_requests.insert(3, '{"foo": "boo"}')
        json_requests = '[%s]' % ','.join(job_requests)
        requests = json.loads(json_requests)
        responses = self.client._run_request(json_requests)

        verify_requests = json.loads("""[
            {"jsonrpc": "2.0", "method": "sum", "params": [1,2,4], "id": "1"},
            {"jsonrpc": "2.0", "method": "notify_hello", "params": [7]},
            {"jsonrpc": "2.0", "method": "subtract",
             "params": [42,23], "id": "2"},
            {"foo": "boo"},
            {"jsonrpc": "2.0", "method": "foo.get",
             "params": {"name": "myself"}, "id": "5"},
            {"jsonrpc": "2.0", "method": "get_data", "id": "9"}
        ]""")

        # Thankfully, these are in order so testing is pretty simple.
        verify_responses = json.loads("""[
            {"jsonrpc": "2.0", "result": 7, "id": "1"},
            {"jsonrpc": "2.0", "result": 19, "id": "2"},
            {"jsonrpc": "2.0",
             "error": {"code": -32600, "message": "Invalid Request."},
             "id": null},
            {"jsonrpc": "2.0",
             "error": {"code": -32601, "message": "Method not found."},
             "id": "5"},
            {"jsonrpc": "2.0", "result": ["hello", 5], "id": "9"}
        ]""")

        self.assertTrue(len(requests) == len(verify_requests))
        self.assertTrue(len(responses) == len(verify_responses))

        responses_by_id = {}
        response_i = 0

        for i in range(len(requests)):
            verify_request = verify_requests[i]
            request = requests[i]
            if request.get('method') != 'notify_hello':
                req_id = request.get('id')
                if 'id' in verify_request:
                    verify_request['id'] = req_id
                verify_response = verify_responses[response_i]
                verify_response['id'] = req_id
                responses_by_id[req_id] = verify_response
                response_i += 1
            self.assertTrue(request == verify_request)

        for response in responses:
            verify_response = responses_by_id.get(response.get('id'))
            if 'error' in verify_response:
                verify_response['error']['message'] = \
                    response['error']['message']
            self.assertTrue(response == verify_response)

    def test_batch_notifications(self):
        """
        Tests a batch call of notifications
        """
        multicall = jsonrpclib.MultiCall(self.client)
        multicall._notify.notify_sum(1, 2, 4)
        multicall._notify.notify_hello(7)
        result = multicall()
        self.assertTrue(len(result) == 0)
        valid_request = json.loads(
            '[{"jsonrpc": "2.0", "method": "notify_sum", ' +
            '"params": [1,2,4]},{"jsonrpc": "2.0", ' +
            '"method": "notify_hello", "params": [7]}]'
        )
        request = json.loads(self.history.request)
        self.assertTrue(len(request) == len(valid_request))
        for i in range(len(request)):
            req = request[i]
            valid_req = valid_request[i]
            self.assertTrue(req == valid_req)
        self.assertTrue(self.history.response == '')

    def test_empty_batch(self):
        """
        Tests the empty batch call
        """
        multicall = jsonrpclib.MultiCall(self.client)
        multicall()

        # No call must have been made
        self.assertIsNone(self.history.request)

    def test_isbatch(self):
        """
        Tests the batch detection method
        """
        # Normal batch
        multicall = jsonrpclib.MultiCall(self.client)
        multicall.sum(1, 2, 4)
        multicall._notify.notify_hello(7)
        multicall.subtract(42, 23)
        multicall()
        request = json.loads(self.history.request)
        self.history.clear()
        self.assertTrue(isbatch(request), "Batch not recognized")

        # Single-call batch
        multicall = jsonrpclib.MultiCall(self.client)
        multicall.sum(1, 2, 4)
        multicall()
        request = json.loads(self.history.request)
        self.history.clear()
        self.assertTrue(isbatch(request), "Batch not recognized")

        # Normal request
        self.client.sum(1, 2, 3)
        request = json.loads(self.history.request)
        self.history.clear()
        self.assertFalse(isbatch(request), "Normal call recognized as batch")

        # JSON-RPC 1.0
        self.assertFalse(isbatch(
            [{"jsonrpc": 1.0, "id": 1,
              "method": "sum", "params": [1, 2]
              }]), "Batch recognized in JSON RPC 1.0")

        # Bad version
        for value in ("", None, "2.0.1", 2j, [2.0]):
            request = [{"jsonrpc": value, "id": 1,
                        "method": "sum", "params": [1, 2]
                        }]
            self.assertRaises(jsonrpclib.ProtocolError, isbatch, request)

        # Bad content
        self.history.clear()
        for request in (
            [], {}, [None], [1, 2], [{1: 2}],
            [{"id": 1, "method": "sum", "params": [1, 2]}],
        ):
            self.assertFalse(
                isbatch(request),
                "Bad query recognized as batch: {}".format(request)
            )

    def test_isnotification(self):
        """
        Tests the notification detection method
        """
        for version in (2, 1):
            config = jsonrpclib.config.DEFAULT.copy()
            config.version = version

            self.client.ping()
            request = json.loads(self.history.request)
            self.assertFalse(isnotification(request))

            self.client._notify.ping()
            request = json.loads(self.history.request)
            self.assertTrue(isnotification(request))
