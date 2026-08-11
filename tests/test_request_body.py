#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Tests the reading of a request body: content encoding and chunked reads.

The body is read from the socket in chunks, which must be joined before being
decoded: a chunk can end in the middle of a multi-byte character, and the
content encoding (gzip) applies to the whole body.

:license: Apache License 2.0
"""

# Standard library
import gzip
import io
import json
import socket
import threading
import unittest

# JSON-RPC library
from jsonrpclib.SimpleJSONRPCServer import (
    SimpleJSONRPCRequestHandler,
    SimpleJSONRPCServer,
)

# Tests utilities
from tests.utilities import raw_post, response_body

# ------------------------------------------------------------------------------

HOST = socket.gethostbyname("localhost")

# A text which needs more than one byte per character in UTF-8.
# It is built from its UTF-8 bytes on purpose: a "u" prefixed literal would be
# needed to get a text string on Python 2, and black (configured for Python
# 3.7) removes those prefixes.
UNICODE_TEXT = (
    b"h\xc3\xa9llo w\xc3\xb6rld \xe6\x97\xa5\xe6\x9c\xac\xe8\xaa\x9e"
).decode("utf-8")


class SmallChunksHandler(SimpleJSONRPCRequestHandler):
    """
    Reads the request body in very small chunks, to get the boundaries of the
    chunks in the middle of the characters and of the compressed stream
    """

    max_chunk_size = 8

    def log_request(self, code="-", size="-"):
        """
        Silences the request logs
        """


def gzip_compress(data):
    """
    Compresses the given bytes with gzip

    :param data: The bytes to compress
    :return: The compressed bytes
    """
    buffer = io.BytesIO()
    handle = gzip.GzipFile(fileobj=buffer, mode="wb")
    try:
        handle.write(data)
    finally:
        handle.close()

    return buffer.getvalue()


# ------------------------------------------------------------------------------


class RequestBodyTests(unittest.TestCase):
    """
    Checks how the body of a request is read
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
            if self.thread is not None:
                self.thread.join(5)
            self.server = None
            self.thread = None

    def start_server(self, handler=None):
        """
        Starts a server with the given request handler

        :param handler: A request handler class
        :return: The port the server listens to
        """
        kwargs = {}
        if handler is not None:
            kwargs["requestHandler"] = handler

        self.server = SimpleJSONRPCServer(
            (HOST, 0), logRequests=False, **kwargs
        )
        self.server.register_function(lambda x: x, "echo")

        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

        return self.server.socket.getsockname()[1]

    def call_echo(self, argument, encoding=None, handler=None):
        """
        Calls the "echo" method of a server with a raw request

        :param argument: The argument given to the method
        :param encoding: The Content-Encoding of the request, if any
        :param handler: A custom request handler class
        :return: The parsed answer of the server
        """
        port = self.start_server(handler)

        # ensure_ascii=False keeps the characters as is, so that the body
        # really holds multi-byte characters a chunk can be cut in.
        # The body is encoded here instead of with utils.to_bytes(), which
        # can't encode non-ASCII characters on Python 2.
        body = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "echo",
                "params": [argument],
            },
            ensure_ascii=False,
        )
        if not isinstance(body, bytes):
            body = body.encode("utf-8")

        headers = "Content-Type: application/json-rpc\r\n"
        if encoding is not None:
            headers += "Content-Encoding: {0}\r\n".format(encoding)
            if encoding == "gzip":
                body = gzip_compress(body)

        headers += "Content-Length: {0}\r\n".format(len(body))
        return raw_post(HOST, port, headers, body)

    def test_identity_request(self):
        """
        Tests a request without any content encoding
        """
        answer = json.loads(response_body(self.call_echo(UNICODE_TEXT)))
        self.assertEqual(UNICODE_TEXT, answer["result"])

    def test_gzip_request(self):
        """
        Tests a request with a gzip-compressed body
        """
        raw = self.call_echo(UNICODE_TEXT, encoding="gzip")
        self.assertIn(b"200", raw.split(b"\r\n")[0])

        answer = json.loads(response_body(raw))
        self.assertEqual(UNICODE_TEXT, answer["result"])

    def test_unsupported_encoding(self):
        """
        Tests that an unsupported content encoding is refused
        """
        raw = self.call_echo("hello", encoding="deflate")
        self.assertIn(b"501", raw.split(b"\r\n")[0])

    def test_multi_chunk_body(self):
        """
        Tests a body read in several chunks, with the boundaries falling in
        the middle of multi-byte characters
        """
        raw = self.call_echo(UNICODE_TEXT, handler=SmallChunksHandler)
        self.assertIn(b"200", raw.split(b"\r\n")[0])

        answer = json.loads(response_body(raw))
        self.assertEqual(UNICODE_TEXT, answer["result"])

    def test_multi_chunk_gzip_body(self):
        """
        Tests a compressed body read in several chunks: the compressed stream
        can only be decoded once it is complete
        """
        raw = self.call_echo(
            UNICODE_TEXT, encoding="gzip", handler=SmallChunksHandler
        )
        self.assertIn(b"200", raw.split(b"\r\n")[0])

        answer = json.loads(response_body(raw))
        self.assertEqual(UNICODE_TEXT, answer["result"])


if __name__ == "__main__":
    unittest.main()
