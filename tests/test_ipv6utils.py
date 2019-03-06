#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Tests the ipv6utils module, to enable double stack servers

:license: Apache License 2.0
"""

# Standard library
import socket
try:
    import unittest2 as unittest
except ImportError:
    import unittest

# JSON-RPC library
from jsonrpclib.ipv6utils import set_double_stack

# ------------------------------------------------------------------------------


class FutureTest(unittest.TestCase):
    """
    Tests the IPv6 utility methods
    """
    def test_double_stack(self):
        """
        Tests the socket double stack activation
        """
        fixed_data = b"Hello, world\n"

        for double_stack in (True, False):
            # Prepare a socket with double stack enabled
            server = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, 0)
            try:
                set_double_stack(server, double_stack)
                server.bind(("::", 0))
                server.listen(1)

                # Get the port the server listens to
                server_port = server.getsockname()[1]

                # Connect it with IPv6 (should work without issue)
                client = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, 0)
                try:
                    client.connect(("::1", server_port))
                    client_conn, _ = server.accept()

                    client.send(fixed_data)
                    client_data = client_conn.recv(len(fixed_data))

                    client_conn.shutdown(socket.SHUT_RDWR)
                    client_conn.close()

                    self.assertEqual(client_data, fixed_data)
                finally:
                    client.close()

                # Connect it with IPv4
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
                try:
                    client.connect(("127.0.0.1", server_port))
                except socket.error:
                    if double_stack:
                        # This shouldn't happen
                        self.fail("IPv4 refused on double-stack socket")
                else:
                    client_conn, _ = server.accept()

                    client.send(fixed_data)
                    client_data = client_conn.recv(len(fixed_data))

                    client_conn.shutdown(socket.SHUT_RDWR)
                    client_conn.close()

                    self.assertEqual(client_data, fixed_data)
                finally:
                    client.close()
            finally:
                # Clean up
                server.close()
