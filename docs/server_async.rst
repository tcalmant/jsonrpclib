.. _server-async:

Asynchronous JSON-RPC Server
****************************

.. warning:: This feature requires Python 3.5+

An asynchronous version of the server protocol is provided by the
``jsonrpclib.server_protocol_async`` module.
The latter provides the :class:`AsyncJsonRpcProtocolHandler` class, which can
be used in any ``asyncio`` protocol implementation.
Currently, the library comes with a server implementation based on the
`aiohttp <https://aiohttp.readthedocs.io>`_ library.

Other implementations can be implemented/contributed.


Sample usage with the ``aiohttp`` implementation
================================================

Imports
-------

The ``aiohttp`` module is not explicitly imported as the ``AiohttpJsonRpcServer``
class hides all the initialization process.
If you want to use a custom ``aiohttp`` instance, you can register the low-level
request handler: ``AiohttpRequestHandler``.

A high level API request handler will be implemented for version 0.5.0.

.. code-block:: python

   import asyncio
   from jsonrpclib.server_protocol_async import AsyncJsonRpcProtocolHandler
   from jsonrpclib.impl.aiohttp_impl import AiohttpRequestHandler, AiohttpJsonRpcServer


Prepare the protocol handler
----------------------------

The first step is the creation of the protocol handler. It has the same API as
the simple JSON-RPC/XML-RPC servers to register functions.

.. code-block:: python

   async def my_async_method():
      # Do something...

   def my_sync_method():
      # Do something...

   # Prepare the protocol handler
   json_handler = AsyncJsonRpcProtocolHandler()

   # Register functions the same way
   json_handler.register_function(my_async_method)
   json_handler.register_function(my_sync_method)

   # Lambda still works
   json_handler.register_function(lambda: "Hello", name="hello")

   # As well as introspection methods
   json_handler.register_introspection_functions()


Asynchronous start method
-------------------------

We then define a utility method that will start the ``aiohttp`` server in the
current event loop. It will also start a *checker* which will wake up every
half second to ensure that Python looks for ``KeyboardInterrupt`` exceptions to
raise from time to time:

.. code-block:: python

   def start_sync(srv):
       loop = asyncio.get_event_loop()
       checker = loop.create_task(srv.async_check_interrupt())
       try:
           loop.run_until_complete(srv.run())
       except KeyboardInterrupt:
           srv.shutdown()
       finally:
           # Wait for the interruption checker
           loop.run_until_complete(checker)


Execution
---------

Here, we can manage the life cycle of the HTTP server.

We first create the HTTP request handler based on ``aiohttp``.
It is a low-level request handler, which is why it's there that we indicate the
path used for JSON-RPC queries.

Then, we prepare the ``aiohttp``-based server itself, indicating its request
handler, binding address and listened port:

.. code-block:: python

   http_handler = AiohttpRequestHandler(json_handler, "/json-rpc")
   srv = AiohttpJsonRpcServer(http_handler, "localhost", 8080)
   try:
       start_sync()
   except KeyboardInterrupt:
       srv.shutdown()

The endpoint is now accessible on http://localhost:8080/json-rpc.


Implement a new asynchronous transport
======================================

.. warning:: TODO

#. Inherit ``AbstractAsyncTransport``
#. Implement ``request(self, host, handler, request_body, verbose=False)``
