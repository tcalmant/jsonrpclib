.. _server-async:

Asynchronous JSON-RPC Server
****************************

.. warning:: This feature requires Python 3.5+

.. warning:: Work in progress

   This feature is a work in progress. This documentation might not updated as
   often as the source code.


An asynchronous version of the server protocol is provided by the
``jsonrpclib.server_protocol_async`` module.
The latter provides the :class:`AsyncJsonRpcProtocolHandler` class, which can
be used in any ``asyncio`` protocol implementation.

The following documentation will use the
`aiohttp <https://aiohttp.readthedocs.io>`_ library.

.. note:: ``aiohttp`` requires Python 3.5.3+ to work.


Sample usage with ``aiohttp``
=============================

.. note:: Use the high-level API of aiohttp

Imports
-------

.. code-block:: python

   import asyncio
   from aiohttp import web
   from jsonrpclib.server_protocol_async import AsyncJsonRpcProtocolHandler


Prepare the protocol handler
----------------------------

The first step is the creation of the protocol handler:

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


Prepare the request handler
---------------------------

The second step is to prepare the request handler that will be used by
``aiohttp``:

.. code-block:: python

   class AsyncRpcRequestHandler:
      """
      Request handler for aiohttp
      """
      def __init__(self, protocol_handler, path):
         """
         :param protocol_handler: The asynchronous JSON-RPC protocol handler
         :param path: Path we'll answer to
         """
         self._protocol_handler = protocol_handler
         self._path = path

      async def request_handler(self, request):
         """
         Handles an HTTP request
         """
         # Sanity check
         if request.method != "POST":
             return web.HTTPMethodNotAllowed(request.method, ["POST"])

         request_path = request.url.path
         if request_path != self._path:
             return web.HTTPNotFound()

         # Parse the body
         request_data = await request.text()
         response = await self._protocol_handler.handle_request_str(request_data)

         result_code = 200
         if isinstance(response, Fault):
             result_code = 500

         if response is not None:
             # Send the response
             return web.json_response(response, status=result_code)
         else:
             # Send an empty response string
             # This is the expected behaviour for notifications and when
             # handling NoMulticallResult
             return web.json_response(body=b"", status=result_code)

.. note:: The two handlers we just created in asynchronous mode are equivalent
   to the HTTP request handler in synchronous mode, as the latter inherits from
   the synchronous protocol handler


Wrapper for the HTTP server
---------------------------

This has been implemented as a workaround for the interruption issue
(Ctrl+C not handled immediately) when using asyncio.

.. code-block:: python

   class AsyncJsonRpcServer:
    def __init__(self, handler: AsyncRpcRequestHandler):
        self._stop_event = asyncio.Event()
        self._handler = handler

    def start_sync(self):
        self._stop_event.clear()

        loop = asyncio.get_event_loop()
        checker = loop.create_task(self.async_check_interrupt())
        try:
            loop.run_until_complete(self.async_server_run())
        except KeyboardInterrupt:
            self._stop_event.set()
        finally:
            # Wait for the interruption checker
            loop.run_until_complete(checker)
            loop.close()

    def shutdown(self):
        self._stop_event.set()

    async def async_check_interrupt(self):
        while not self._stop_event.is_set():
            await asyncio.sleep(0.5)

    async def async_server_run(self):
        server = web.Server(self._handler.request_handler)
        runner = web.ServerRunner(server)
        print("Setting up...")
        await runner.setup()
        print("Done setup.")

        site = web.TCPSite(runner, "localhost", 8080)
        print("Starting...")
        await site.start()
        print("Servicing on", site._server.sockets[0].getsockname()[1])

        # Wait the server shutdown message
        await self._stop_event.wait()

        # Clean up
        await site.stop()
        await runner.shutdown()

Execution
---------

Finally, we can run the HTTP server.


.. code-block:: python

   srv = AsyncJsonRpcServer(AsyncRpcRequestHandler(json_handler, "/json-rpc"))
   try:
       srv.start_sync()
   except KeyboardInterrupt:
       srv.shutdown()
