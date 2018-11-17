Welcome to JSONRPClib-pelix
###########################

This library is an implementation of the JSON-RPC specification.
It supports both the original 1.0 specification, as well as the
new (proposed) 2.0 specification, which includes batch submission, keyword
arguments, etc.

It is licensed under the
`Apache License, Version 2.0 <http://www.apache.org/licenses/LICENSE-2.0.html>`_.

.. toctree::
   :maxdepth: 2

   installation
   client
   server
   class_translation
   license


Why JSON-RPC?
*************

In my opinion, there are several reasons to choose JSON over XML for RPC:

* Much simpler to read (I suppose this is opinion, but I know I'm right. :)
* Size / Bandwidth - Main reason, a JSON object representation is just much smaller.
* Parsing - JSON should be much quicker to parse than XML.
* Easy class passing with ``jsonclass`` (when enabled)

In the interest of being fair, there are also a few reasons to choose XML
over JSON:

* Your server doesn't do JSON (rather obvious)
* Wider XML-RPC support across APIs (can we change this? :))
* Libraries are more established, i.e. more stable (Let's change this too.)


About this version
******************

This is a patched version of the original ``jsonrpclib`` project by
Josh Marshall, available at https://github.com/joshmarshall/jsonrpclib.

The suffix *-pelix* only indicates that this version works with Pelix Remote
Services, but it is **not** a Pelix specific implementation.

* This version adds support for Python 3, staying compatible with Python 2.7.
* It is now possible to use the dispatch_method argument while extending
  the SimpleJSONRPCDispatcher, to use a custom dispatcher.
  This allows to use this package by Pelix Remote Services.
* It can use thread pools to control the number of threads spawned to handle
  notification requests and clients connections.
* The modifications added in other forks of this project have been added:

  * From https://github.com/drdaeman/jsonrpclib:

    * Improved JSON-RPC 1.0 support
    * Less strict error response handling

  * From https://github.com/tuomassalo/jsonrpclib:

    * In case of a non-pre-defined error, raise an AppError and give access to
      *error.data*

  * From https://github.com/dejw/jsonrpclib:

    * Custom headers can be sent with request and associated tests

* The support for Unix sockets has been removed, as it is not trivial to convert
  to Python 3 (and I don't use them)
* This version cannot be installed with the original ``jsonrpclib``, as it uses
  the same package name.
