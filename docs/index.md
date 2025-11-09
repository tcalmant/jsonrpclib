# Welcome to JSONRPClib-pelix

This library implements the JSON-RPC 2.0 proposed specification in pure Python.
It is designed to be as compatible with the syntax of `xmlrpclib` as possible
(it extends where possible), so that projects using `xmlrpclib` could easily
be modified to use JSON and experiment with the differences.

It is backwards-compatible with the 1.0 specification, and supports all of the
new proposed features of 2.0, including:

- Batch submission (via the `MultiCall` class)
- Keyword arguments
- Notifications (both in a batch and *normal*)
- Class translation using the `__jsonclass__` key.

A `SimpleJSONRPCServer` class has been added. It is intended to emulate the
`SimpleXMLRPCServer` from the default Python distribution.

This library is licensed under the terms of the [Apache Software License 2.0](https://www.apache.org/licenses/LICENSE-2.0.html).

```{toctree}
:maxdepth: 2

installation
client
server
class_translation
```

```{toctree}
:maxdepth: 1

changelog
license
```

## Why JSON-RPC?

In my opinion, there are several reasons to choose JSON over XML for RPC:

- Much simpler to read (I suppose this is opinion, but I know I'm right. :)
- Size / Bandwidth - Main reason, a JSON object representation is just much smaller.
- Parsing - JSON should be much quicker to parse than XML.
- Easy class passing with `jsonclass` (when enabled)

In the interest of being fair, there are also a few reasons to choose XML
over JSON:

- Your server doesn't do JSON (rather obvious)
- Wider XML-RPC support across APIs (can we change this? :))
- Libraries are more established, i.e. more stable (Let's change this too.)

## About this version

This is a patched version of the original `jsonrpclib` project by
Josh Marshall, available at [joshmarshall/jsonrpclib](https://github.com/joshmarshall/jsonrpclib).

The suffix *-pelix* only indicates that this version works with Pelix Remote
Services, but **it is not** a Pelix specific implementation.

- This version adds support for Python 3, staying compatible with Python 2.7.
- It is now possible to use the dispatch_method argument while extending
  the SimpleJSONRPCDispatcher, to use a custom dispatcher.
  This allows to use this package by Pelix Remote Services.
- It can use thread pools to control the number of threads spawned to handle
  notification requests and clients connections.
- The modifications added in other forks of this project have been added:

  - From [drdaeman/jsonrpclib](https://github.com/drdaeman/jsonrpclib):

    - Improved JSON-RPC 1.0 support
    - Less strict error response handling

  - From [tuomassalo/jsonrpclib](https://github.com/tuomassalo/jsonrpclib):

    - In case of a non-pre-defined error, raise an AppError and give access to
      *error.data*

  - From [dejw/jsonrpclib](https://github.com/dejw/jsonrpclib):

    - Custom headers can be sent with request and associated tests

- Since version 0.4, this package added back the support of Unix sockets.
- This version cannot be installed with the original `jsonrpclib`, as it uses
  the same package name.
