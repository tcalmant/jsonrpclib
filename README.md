# JSONRPClib (patched for Pelix and Python 3)

[![Latest Version](https://img.shields.io/pypi/v/jsonrpclib-pelix.svg)](https://pypi.python.org/pypi/jsonrpclib-pelix/)
[![License](https://img.shields.io/pypi/l/jsonrpclib-pelix.svg)](https://pypi.python.org/pypi/jsonrpclib-pelix/)
[![CI Build](https://github.com/tcalmant/jsonrpclib/actions/workflows/build-24.04.yml/badge.svg?branch=master)](https://github.com/tcalmant/jsonrpclib/actions/workflows/build-24.04.yml)
[![Coveralls status](https://coveralls.io/repos/tcalmant/jsonrpclib/badge.svg?branch=master)](https://coveralls.io/r/tcalmant/jsonrpclib?branch=master)

This library is an implementation of the JSON-RPC specification.
It supports both the original 1.0 specification, as well as the new
(proposed) 2.0 specification, which includes batch submission, keyword
arguments, etc.

This library is licensed under the terms of the
[Apache Software License 2.0](<http://www.apache.org/licenses/LICENSE-2.0.html>).


## About this version

This is a patched version of the original `jsonrpclib` project by Josh Marshall,
available at
[joshmarshall/jsonrpclib](<https://github.com/joshmarshall/jsonrpclib>).

The suffix *-pelix* only indicates that this version works with Pelix
Remote Services, but it is **not** a Pelix specific implementation.

* This version adds support for Python 3, staying compatible with Python 2.7.
  The support for Python 2.6 has been dropped, as it was becoming to hard to
  maintain.
* It is now possible to use the `dispatch_method` argument while extending the
  `SimpleJSONRPCDispatcher`, to use a custom dispatcher.
  This allows to use this package by Pelix Remote Services.
* It can use thread pools to control the number of threads spawned to handle
  notification requests and clients connections.
* The modifications added in other forks of this project have been added:
    * From [drdaeman/jsonrpclib](<https://github.com/drdaeman/jsonrpclib>):
      * Improved JSON-RPC 1.0 support
      * Less strict error response handling
    * From [tuomassalo/jsonrpclib](<https://github.com/tuomassalo/jsonrpclib>):
      * In case of a non-predefined error, raise an AppError and give access
        to *error.data*
    * From [dejw/jsonrpclib](<https://github.com/dejw/jsonrpclib>):
      * Custom headers can be sent with request and associated tests
* Since version 0.4, this package added back the support of Unix sockets.
* This package cannot be installed with the original `jsonrpclib`, as it uses
  the same name.

## Summary

This library implements the JSON-RPC 2.0 proposed specification in pure Python.
It is designed to be as compatible with the syntax of `xmlrpclib` as possible
(it extends where possible), so that projects using `xmlrpclib` could easily be
modified to use JSON and experiment with the differences.

It is backwards-compatible with the 1.0 specification, and supports all of the
new proposed features of 2.0, including:

- Batch submission (via the `MultiCall` class)
- Keyword arguments
- Notifications (both in a batch and 'normal')
- Class translation using the `__jsonclass__` key.

A `SimpleJSONRPCServer` class has been added. It is intended to emulate the
`SimpleXMLRPCServer` from the default Python distribution.

## Requirements

This library supports `orjson`, `ujson`, `cjson` and `simplejson`, and looks
for the parsers in that order (searching first for `orjson`, `ujson`, `cjson`,
`simplejson` and finally for the *built-in* `json`).
One of these must be installed to use this library, although if you have a
standard distribution of 2.7+, you should already have one.
Keep in mind that `orjson` is supposed to be the quickest, I believe, so if you
are going for full-on optimization you may want to pick it up.

## Installation

You can install this from PyPI with one of the following commands (`sudo`
might be required):

```
# Global installation
pip install jsonrpclib-pelix

# Local installation
pip install --user jsonrpclib-pelix
```

Alternatively, you can download the source from the GitHub repository at
[tcalmant/jsonrpclib](http://github.com/tcalmant/jsonrpclib) and manually
install it with the following commands:

```
git clone git://github.com/tcalmant/jsonrpclib.git
cd jsonrpclib
python setup.py install
```

## A note on logging

`jsonrpclib-pelix` uses the `logging` module from the standard Python
library to trace warnings and errors, but doesn't set it up.
As a result, you have to configure the Python logging to print out traces.

The easiest way to do it is to add those lines at the beginning of your code:
```python
import logging
logging.basiConfig()
```

More information can be found in the
[`logging` documentation page](https://docs.python.org/3/library/logging.html).

## `SimpleJSONRPCServer`

This is identical in usage (or should be) to the `SimpleXMLRPCServer` in the
Python standard library.
Some of the differences in features are that it obviously supports notification,
batch calls, class translation (if left on), etc.

**Note:** The import line is slightly different from the regular
`SimpleXMLRPCServer`, since the `SimpleJSONRPCServer` is provided by th
`jsonrpclib` library.

```python
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer

server = SimpleJSONRPCServer(('localhost', 8080))
server.register_function(pow)
server.register_function(lambda x,y: x+y, 'add')
server.register_function(lambda x: x, 'ping')
server.serve_forever()
```

To start protect the server with SSL, use the following snippet:

```python
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer
import ssl

# Setup the SSL socket
server = SimpleJSONRPCServer(('localhost', 8080), bind_and_activate=False)
server.socket = ssl.wrap_socket(server.socket, certfile='server.pem',
                                server_side=True)
server.server_bind()
server.server_activate()

# ... register functions
# Start the server
server.serve_forever()
```

### Notification Thread Pool

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

### Threaded server

It is also possible to use a thread pool to handle clients requests, using the
`PooledJSONRPCServer` class.
By default, this class uses pool of 0 to 30 threads.
A custom pool can be given with the `thread_pool` parameter of the class
constructor.

The notification pool and the request pool are different: by default, a server
with a request pool doesn't have a notification pool.

```python
from jsonrpclib.SimpleJSONRPCServer import PooledJSONRPCServer
from jsonrpclib.threadpool import ThreadPool

# Setup the notification and request pools
nofif_pool = ThreadPool(max_threads=10, min_threads=0)
request_pool = ThreadPool(max_threads=50, min_threads=10)

# Don't forget to start them
nofif_pool.start()
request_pool.start()

# Setup the server
server = PooledJSONRPCServer(('localhost', 8080), thread_pool=request_pool)
server.set_notification_pool(nofif_pool)

# Register methods
server.register_function(pow)
server.register_function(lambda x,y: x+y, 'add')
server.register_function(lambda x: x, 'ping')

try:
    server.serve_forever()
finally:
    # Stop the thread pools (let threads finish their current task)
    request_pool.stop()
    nofif_pool.stop()
    server.set_notification_pool(None)
```

### Unix socket

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
   srv = SimpleJSONRPCServer(socket_name, address_family=socket.AF_UNIX)

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

This feature is tested on Linux during Travis-CI builds. It also has
been tested on Windows Subsystem for Linux (WSL) on Windows 10 1809.

This feature is not available on "pure" Windows, as it doesn't provide
the `AF_UNIX` address family.

## Client Usage

This is (obviously) taken from a console session.

```python
>>> import jsonrpclib
>>> server = jsonrpclib.ServerProxy('http://localhost:8080')
>>> server.add(5,6)
11
>>> server.add(x=5, y=10)
15
>>> server._notify.add(5,6)
# No result returned...
>>> batch = jsonrpclib.MultiCall(server)
>>> batch.add(5, 6)
>>> batch.ping({'key':'value'})
>>> batch._notify.add(4, 30)
>>> results = batch()
>>> for result in results:
>>> ... print(result)
11
{'key': 'value'}
# Note that there are only two responses -- this is according to spec.

# Clean up
>>> server('close')()

# Using client history
>>> history = jsonrpclib.history.History()
>>> server = jsonrpclib.ServerProxy('http://localhost:8080', history=history)
>>> server.add(5,6)
11
>>> print(history.request)
{"id": "f682b956-c8e1-4506-9db4-29fe8bc9fcaa", "jsonrpc": "2.0",
 "method": "add", "params": [5, 6]}
>>> print(history.response)
{"id": "f682b956-c8e1-4506-9db4-29fe8bc9fcaa", "jsonrpc": "2.0",
 "result": 11}

# Clean up
>>> server('close')()
```

If you need 1.0 functionality, there are a bunch of places you can pass
that in, although the best is just to give a specific configuration to
`jsonrpclib.ServerProxy`:

```python
>>> import jsonrpclib
>>> jsonrpclib.config.DEFAULT.version
2.0
>>> config = jsonrpclib.config.Config(version=1.0)
>>> history = jsonrpclib.history.History()
>>> server = jsonrpclib.ServerProxy('http://localhost:8080', config=config,
                                    history=history)
>>> server.add(7, 10)
17
>>> print(history.request)
{"id": "827b2923-5b37-49a5-8b36-e73920a16d32",
 "method": "add", "params": [7, 10]}
>>> print(history.response)
{"id": "827b2923-5b37-49a5-8b36-e73920a16d32", "error": null, "result": 17}
>>> server('close')()
```

The equivalent `loads` and `dumps` functions also exist, although with
minor modifications.
The `dumps` arguments are almost identical, but it adds three arguments:
`rpcid` for the `id` key, `version` to specify the JSON-RPC compatibility,
and `notify` if it's a request that you want to be a notification.

Additionally, the `loads` method does not return the params and method like
`xmlrpclib`, but instead
a.) parses for errors, raising ProtocolErrors, and
b.) returns the entire structure of the request / response for manual parsing.

### Unix sockets

To connect a JSON-RPC server over a Unix socket, you have to use a specific
protocol: `unix+http`.

When connecting to a Unix socket in the current working directory, you can use
the following syntax: `unix+http://my.socket`

When you need to give an absolute path you must use the path part of the URL,
the host part will be ignored. For example, you can use this URL to indicate a
Unix socket in `/var/lib/daemon.socket`: `unix+http://./var/lib/daemon.socket`

**Note:** Currently, only HTTP is supported over a Unix socket.
If you want HTTPS support to be implemented, please create an
[issue on GitHub](https://github.com/tcalmant/jsonrpclib/issues)

### Additional headers

If your remote service requires custom headers in request, you can pass them
using the `headers` keyword argument, when creating the `ServerProxy`:

```python
>>> import jsonrpclib
>>> server = jsonrpclib.ServerProxy("http://localhost:8080",
                                    headers={'X-Test' : 'Test'})
```

You can also put additional request headers only for certain method
invocation:

```python
>>> import jsonrpclib
>>> server = jsonrpclib.Server("http://localhost:8080")
>>> with server._additional_headers({'X-Test' : 'Test'}) as test_server:
...     test_server.ping(42)
...
>>> # X-Test header will be no longer sent in requests
```

Of course `_additional_headers` contexts can be nested as well.

## Class Translation

The library supports an *"automatic"* class translation process, although it
is turned off by default.
This can be devastatingly slow if improperly used, so the following is just a
short list of things to keep in mind when using it.

- Keep It (the object) Simple Stupid. (for exceptions, keep reading)
- Do not require init params (for exceptions, keep reading)
- Getter properties without setters could be dangerous (read: not tested)

If any of the above are issues, use the `_serialize` method (see usage below).
The server and client must **BOTH** have the `use_jsonclass` configuration
item on and they must both have access to the same libraries used by the
objects for this to work.

If you have excessively nested arguments, it would be better to turn off the
translation and manually invoke it on specific objects using
`jsonrpclib.jsonclass.dump` / `jsonrpclib.jsonclass.load` (since the
default behavior recursively goes through attributes and lists/dicts/tuples).

* Sample file: `test_obj.py`

```python
# This object is /very/ simple, and the system will look through the
# attributes and serialize what it can.
class TestObj(object):
    foo = 'bar'

# This object requires __init__ params, so it uses the _serialize method
# and returns a tuple of init params and attribute values (the init params
# can be a dict or a list, but the attribute values must be a dict.)
class TestSerial(object):
    foo = 'bar'
    def __init__(self, *args):
        self.args = args
    def _serialize(self):
        return (self.args, {'foo':self.foo,})
```

- Sample usage:

```python
>>> import jsonrpclib
>>> import test_obj

# History is used only to print the serialized form of beans
>>> history = jsonrpclib.history.History()
>>> testobj1 = test_obj.TestObj()
>>> testobj2 = test_obj.TestSerial()
>>> server = jsonrpclib.Server('http://localhost:8080', history=history)

# The 'ping' just returns whatever is sent
>>> ping1 = server.ping(testobj1)
>>> ping2 = server.ping(testobj2)

>>> print(history.request)
{"id": "7805f1f9-9abd-49c6-81dc-dbd47229fe13", "jsonrpc": "2.0",
 "method": "ping", "params": [{"__jsonclass__":
                               ["test_obj.TestSerial", []], "foo": "bar"}
                             ]}
>>> print(history.response)
{"id": "7805f1f9-9abd-49c6-81dc-dbd47229fe13", "jsonrpc": "2.0",
 "result": {"__jsonclass__": ["test_obj.TestSerial", []], "foo": "bar"}}
```

This behavior is turned on by default.
To deactivate it, just set the `use_jsonclass` member of a server `Config` to
`False`.
If you want to use a per-class serialization method, set its name in the
`serialize_method` member of a server `Config`.
Finally, if you are using classes that you have defined in the implementation
(as in, not a separate library), you'll need to add those
(on **BOTH** the server and the client) using the `config.classes.add()` method.

Feedback on this "feature" is very, VERY much appreciated.

## Tests

Tests are an almost-verbatim drop from the JSON-RPC specification 2.0
page. They can be run using *unittest* or *nosetest*:

```
python -m unittest discover tests
python3 -m unittest discover tests
nosetests tests
```

## Why JSON-RPC?

In my opinion, there are several reasons to choose JSON over XML for RPC:

* Much simpler to read (I suppose this is opinion, but I know I'm right. :)
* Size / Bandwidth - Main reason, a JSON object representation is just much
  smaller.
* Parsing - JSON should be much quicker to parse than XML.
* Easy class passing with `jsonclass` (when enabled)

In the interest of being fair, there are also a few reasons to choose XML over
JSON:

* Your server doesn't do JSON (rather obvious)
* Wider XML-RPC support across APIs (can we change this? :))
* Libraries are more established, *i.e.* more stable (Let's change this too)
