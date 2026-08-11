# Simple JSON-RPC Server

This is identical in usage (or should be) to the `SimpleXMLRPCServer` in the
Python standard library. Some of the differences in features are that it
obviously supports notification, batch calls, class translation (if left on),
etc.

:::{note}
The import line is slightly different from the regular
`SimpleXMLRPCServer`, since the `SimpleJSONRPCServer` is provided by the
`jsonrpclib` library.
:::

```python
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer

server = SimpleJSONRPCServer(('localhost', 8080))
server.register_function(pow)
server.register_function(lambda x,y: x+y, 'add')
server.register_function(lambda x: x, 'ping')
server.serve_forever()
```

To protect the server with SSL, use the following snippet:

```python
import ssl
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer

# Setup the SSL socket
server = SimpleJSONRPCServer(
    ('localhost', 8080), bind_and_activate=False)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(certfile='server.pem')
server.socket = context.wrap_socket(server.socket, server_side=True)
server.server_bind()
server.server_activate()

# ... register functions

# Start the server
server.serve_forever()
```

```{note}
`ssl.wrap_socket()`, which this snippet used to rely on, was removed in
Python 3.12.
On Python 2.7, use `ssl.PROTOCOL_TLSv1_2` instead of
`ssl.PROTOCOL_TLS_SERVER`, which doesn't exist there.
```

Clients then connect using an `https://` URL.
A custom SSL context can be given to `ServerProxy` with the `context`
argument, *e.g.* to trust a self-signed certificate:

```python
import ssl

import jsonrpclib

context = ssl.create_default_context(cafile='server-cert.pem')
client = jsonrpclib.ServerProxy('https://localhost:8080', context=context)
```

## Maximum Request Size

The request handler supports limiting the maximum accepted request body size
through `MAX_REQUEST_SIZE`.

The default value is `0`, which means **unlimited** and therefore preserves
the previous behavior.

To configure a limit for one server, subclass
`SimpleJSONRPCRequestHandler` and override `max_request_size`:

```python
from jsonrpclib.SimpleJSONRPCServer import (
    SimpleJSONRPCRequestHandler,
    SimpleJSONRPCServer,
)


class LimitedRequestHandler(SimpleJSONRPCRequestHandler):
    # Limit request body to 1 MiB
    max_request_size = 1024 * 1024


server = SimpleJSONRPCServer(
    ('localhost', 8080), requestHandler=LimitedRequestHandler)
```

When the limit is exceeded, the server responds with `HTTP 413`
(`Request Entity Too Large`).

## A note on logging

`jsonrpclib-pelix` uses the `logging` module from the standard Python
library to trace warnings and errors, but doesn't set it up.
As a result, you have to configure the Python logging to print out traces.

The easiest way to do it is to add those lines at the beginning of your code:

```python
import logging
logging.basicConfig()
```

More information can be found in the
[logging documentation page](https://docs.python.org/3/library/logging.html).

## Notification Thread Pool

By default, notification calls are handled in the request handling thread.
It is possible to use a thread pool to handle them, by giving it to the server
using the `set_notification_pool()` method:

```python
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer
from jsonrpclib.threadpool import ThreadPool

# Setup the thread pool: between 0 and 10 threads
pool = ThreadPool(max_threads=10, min_threads=0)

# Don't forget to start it
pool.start()

# Setup the server
server = SimpleJSONRPCServer(('localhost', 8080))
server.set_notification_pool(pool)

# Register methods
server.register_function(pow)
server.register_function(lambda x,y: x+y, 'add')
server.register_function(lambda x: x, 'ping')

try:
    server.serve_forever()
finally:
    # Stop the thread pool (let threads finish their current task)
    pool.stop()
    server.set_notification_pool(None)
```

## Threaded server

It is also possible to use a thread pool to handle clients requests, using the
`PooledJSONRPCServer` class.
By default, this class uses pool of 0 to 30 threads. A custom pool can be given
with the `thread_pool` parameter of the class constructor.

The notification pool and the request pool are different: by default, a server
with a request pool doesn't have a notification pool.

```python
from jsonrpclib.SimpleJSONRPCServer import PooledJSONRPCServer
from jsonrpclib.threadpool import ThreadPool

# Setup the notification and request pools
notification_pool = ThreadPool(max_threads=10, min_threads=0)
request_pool = ThreadPool(max_threads=50, min_threads=10)

# Don't forget to start them
notification_pool.start()
request_pool.start()

# Setup the server
server = PooledJSONRPCServer(
    ('localhost', 8080), thread_pool=request_pool)
server.set_notification_pool(notification_pool)

# Register methods
server.register_function(pow)
server.register_function(lambda x,y: x+y, 'add')
server.register_function(lambda x: x, 'ping')

try:
    server.serve_forever()
finally:
    # Stop the thread pools (let threads finish their current task)
    request_pool.stop()
    notification_pool.stop()
    server.set_notification_pool(None)
```

## Unix Socket

To start a server listening on a Unix socket, you will have to use the
following snippet:

```python
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer
import os
import socket

# Set the path to the socket file
socket_name = "/tmp/my_socket.socket"

# Ensure that the file doesn't exist yet (or an error will be raised)
if os.path.exists(socket_name):
    os.remove(socket_name)

try:
    # Start the server, indicating the socket family
    # The server will force some flags when in Unix socket mode
    # (no log request, no reuse address, ...)
    srv = SimpleJSONRPCServer(
        socket_name, address_family=socket.AF_UNIX)

    # ... register methods to the server
    # Run the server
    srv.serve_forever()
except KeyboardInterrupt:
    # Shutdown the server gracefully
    srv.shutdown()
    srv.server_close()
finally:
    # You should clean up after the server stopped
    os.remove(socket_name)
```

This feature is tested on Linux during GitHub CI builds. It also has
been tested on Windows Subsystem for Linux (WSL) on Windows 10 1809.

This feature is not available on "pure" Windows, as it doesn't provide
the `AF_UNIX` address family.
