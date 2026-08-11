#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Tests utility classes

:license: Apache License 2.0
"""

# Standard library
import socket
import threading

# JSON-RPC library
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer
from jsonrpclib.utils import to_bytes

# ------------------------------------------------------------------------------
# Test methods


def subtract(minuend, subtrahend):
    """
    Using the keywords from the JSON-RPC v2 doc
    """
    return minuend - subtrahend


def add(x, y):
    """
    Sample addition, positional arguments
    """
    return x + y


def update(*args):
    """
    Sample with a list of optional arguments (returns the list)
    """
    return args


def summation(*args):
    """
    Sample with a list of optional arguments (returns the sum of the arguments)
    """
    return sum(args)


def notify_hello(*args):
    """
    Sample with a list of optional arguments (returns the list), meant to be
    called as a notification
    """
    return args


def get_data():
    """
    Returns a list with a string and an integer
    """
    return ["hello", 5]


def ping():
    """
    No argument, returns a boolean
    """
    return True


def fail():
    """
    No argument, raises an exception
    """
    raise ValueError("Everything I do fails")


# ------------------------------------------------------------------------------
# Raw HTTP utility


def raw_post(host, port, headers, body=b""):
    """
    Sends a raw HTTP POST request to a test server.

    Used to send the requests a ServerProxy can't send, e.g. an invalid
    framing or a body which isn't valid JSON.

    :param host: The host of the server
    :param port: The port the server listens to
    :param headers: The headers of the request, as a string (each one ending
                    with CRLF)
    :param body: The raw body of the request
    :return: The raw answer of the server
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        sock.connect((host, port))
        sock.sendall(
            to_bytes(
                "POST / HTTP/1.0\r\nHost: {0}\r\n{1}\r\n".format(host, headers)
            )
            + body
        )

        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
    finally:
        sock.close()

    return response


def response_body(raw_response):
    """
    Extracts the body of a raw HTTP response

    :param raw_response: A raw HTTP response, as bytes
    :return: The body of the response, as a string
    """
    body = raw_response.split(b"\r\n\r\n", 1)[-1]
    return body.decode("utf-8", "replace")


# ------------------------------------------------------------------------------
# Server utility class


class UtilityServer(object):
    """
    Utility start/stop server
    """

    def __init__(self):
        """
        Sets up members
        """
        self._server = None
        self._thread = None

    def start(self, addr, port):
        """
        Starts the server

        :param addr: A binding address
        :param port: A listening port
        :return: This object (for in-line calls)
        """
        # Create the server
        self._server = server = SimpleJSONRPCServer(
            (addr, port), logRequests=False
        )

        # Register test methods
        server.register_function(summation, "sum")
        server.register_function(summation, "notify_sum")
        server.register_function(notify_hello)
        server.register_function(subtract)
        server.register_function(update)
        server.register_function(get_data)
        server.register_function(add)
        server.register_function(ping)
        server.register_function(summation, "namespace.sum")
        server.register_function(fail)

        # Serve in a thread
        self._thread = threading.Thread(target=server.serve_forever)
        self._thread.daemon = True
        self._thread.start()

        # Allow an in-line instantiation
        return self

    def get_port(self):
        """
        Retrieves the port this server is listening to
        """
        return self._server.socket.getsockname()[1]

    def stop(self):
        """
        Stops the server and waits for its thread to finish
        """
        self._server.shutdown()
        self._server.server_close()
        self._thread.join()

        self._server = None
        self._thread = None
