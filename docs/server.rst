.. _server:

Simple JSON-RPC Server
**********************

This is identical in usage (or should be) to the ``SimpleXMLRPCServer`` in the
Python standard library. Some of the differences in features are that it
obviously supports notification, batch calls, class translation (if left on),
etc.
Note: The import line is slightly different from the regular
``SimpleXMLRPCServer``, since the ``SimpleJSONRPCServer`` is provided by the
``jsonrpclib`` library.

.. code-block:: python

   from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer

   server = SimpleJSONRPCServer(('localhost', 8080))
   server.register_function(pow)
   server.register_function(lambda x,y: x+y, 'add')
   server.register_function(lambda x: x, 'ping')
   server.serve_forever()

To start protect the server with SSL, use the following snippet:

.. code-block:: python

   from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer

   # Setup the SSL socket
   server = SimpleJSONRPCServer(('localhost', 8080), bind_and_activate=False)
   server.socket = ssl.wrap_socket(server.socket, certfile='server.pem',
                                   server_side=True)
   server.server_bind()
   server.server_activate()

   # ... register functions
   # Start the server
   server.serve_forever()


Notification Thread Pool
========================

By default, notification calls are handled in the request handling thread.
It is possible to use a thread pool to handle them, by giving it to the server
using the ``set_notification_pool()`` method:

.. code-block:: python

   from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer
   from jsonrpclib.threadpool import ThreadPool

   # Setup the thread pool: between 0 and 10 threads
   pool = ThreadPool(max_threads=10, min_threads=0)

   # Don't forget to start it
   pool.start()

   # Setup the server
   server = SimpleJSONRPCServer(('localhost', 8080), config)
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


Threaded server
===============

It is also possible to use a thread pool to handle clients requests, using the
``PooledJSONRPCServer`` class.
By default, this class uses pool of 0 to 30 threads. A custom pool can be given
with the ``thread_pool`` parameter of the class constructor.

The notification pool and the request pool are different: by default, a server
with a request pool doesn't have a notification pool.

.. code-block:: python

   from jsonrpclib.SimpleJSONRPCServer import PooledJSONRPCServer
   from jsonrpclib.threadpool import ThreadPool

   # Setup the notification and request pools
   nofif_pool = ThreadPool(max_threads=10, min_threads=0)
   request_pool = ThreadPool(max_threads=50, min_threads=10)

   # Don't forget to start them
   nofif_pool.start()
   request_pool.start()

   # Setup the server
   server = PooledJSONRPCServer(('localhost', 8080), config,
                                thread_pool=request_pool)
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

Unix Socket
===========

To start a server listening on a Unix socket, you will have to use the
following snippet:

.. code-block:: python

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

This feature is tested on Linux during Travis-CI builds. It also has
been tested on Windows Subsystem for Linux (WSL) on Windows 10 1809.

This feature is not available on "pure" Windows, as it doesn't provide
the ``AF_UNIX`` address family.
