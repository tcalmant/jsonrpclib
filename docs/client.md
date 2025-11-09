# JSON-RPC Client usage

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

If you need 1.0 functionality, there are a bunch of places you can pass that in,
although the best is just to give a specific configuration to
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

The equivalent `loads` and `dumps` functions also exist, although with minor
modifications. The `dumps` arguments are almost identical, but it adds three
arguments: `rpcid` for the 'id' key, `version` to specify the JSON-RPC
compatibility, and `notify` if it's a request that you want to be a
notification.

Additionally, the `loads` method does not return the params and method like
`xmlrpclib`, but instead:

1. parses for errors, raising `ProtocolError`s, and
2. returns the entire structure of the request / response for manual parsing.

## Unix Socket

To connect a JSON-RPC server over a Unix socket, you have to use a specific
protocol: `unix+http`.

When connecting to a Unix socket in the current working directory, you can use
the following syntax: `unix+http://my.socket`

When you need to give an absolute path you must use the path part of the URL,
the host part will be ignored. For example, you can use this URL to indicate a
Unix socket in `/var/lib/daemon.socket`:
`unix+http://./var/lib/daemon.socket`

**Note:** Currently, only HTTP is supported over a Unix socket.
If you want HTTPS support to be implemented, please create an
[issue on GitHub](https://github.com/tcalmant/jsonrpclib/issues).

## Additional headers

If your remote service requires custom headers in request, you can pass them
as a `headers` keyword argument, when creating the `ServerProxy`:

```python
>>> import jsonrpclib
>>> server = jsonrpclib.ServerProxy(
...     "http://localhost:8080", headers={'X-Test' : 'Test'})
```

You can also put additional request headers only for certain method invocation:

```python
>>> import jsonrpclib
>>> server = jsonrpclib.ServerProxy("http://localhost:8080")
>>> with server._additional_headers({'X-Test' : 'Test'}) as test_server:
...     test_server.ping(42)
...
>>> # X-Test header will be no longer sent in requests
```

Of course `_additional_headers` contexts can be nested as well.
