.. _client-async:

Asynchronous JSON-RPC Client
****************************

.. warning:: This feature requires Python 3.5+

.. warning:: Work in progress

   This feature is a work in progress. This documentation might not updated as
   often as the source code.


An asynchronous version of the client implementation is provided by the
``jsonrpclib.jsonrpc_async`` module.
The latter provides the :class:`AsyncServerProxy` class, which uses an
asynchronous `Transport` implementation.
Currently, the only provided `Transport` is based on `aiohttp`.

The following documentation will use the
`aiohttp <https://aiohttp.readthedocs.io>`_ library.

.. note:: ``aiohttp`` requires Python 3.5.3+ to work.


Sample usage
============

This sample shows how easy it is to use the new API.

.. warning::

   In the current state of development, the ``AsyncServerProxy`` uses
   `aiohttp` under the hood.

   The next step will be to allow the developer to use a custom `Transport`
   implementation.

.. code-block:: python

   import asyncio

   from jsonrpclib.jsonrpc_async import AsyncServerProxy

   async def main():
       """
       Script entry point
       """
       # As easy as it can be
       server = AsyncServerProxy("http://localhost:8080")
       print(await server.pow(2, 4096))


   if __name__ == "__main__":
       # Use an event loop to run the asynchronous entry point
       loop = asyncio.get_event_loop()
       loop.run_until_complete(main())
