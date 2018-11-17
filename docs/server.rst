.. _server:

Simple JSON-RPC Server
**********************

This is identical in usage (or should be) to the SimpleXMLRPCServer in the
Python standard library. Some of the differences in features are that it
obviously supports notification, batch calls, class translation (if left on),
etc.
Note: The import line is slightly different from the regular SimpleXMLRPCServer,
since the SimpleJSONRPCServer is distributed within the ``jsonrpclib`` library.

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


Additional headers
==================

If your remote service requires custom headers in request, you can pass them
as as a ``headers`` keyword argument, when creating the ``ServerProxy``:

.. code-block:: python

   >>> import jsonrpclib
   >>> server = jsonrpclib.ServerProxy("http://localhost:8080",
                                       headers={'X-Test' : 'Test'})

You can also put additional request headers only for certain method invocation:

.. code-block:: python

   >>> import jsonrpclib
   >>> server = jsonrpclib.Server("http://localhost:8080")
   >>> with server._additional_headers({'X-Test' : 'Test'}) as test_server:
   ...     test_server.ping(42)
   ...
   >>> # X-Test header will be no longer sent in requests

Of course ``_additional_headers`` contexts can be nested as well.
