.. _changelog:

Release Notes
#############

0.4.2
=====

:Release Date: 2020-11-09

* Use ``urlparse`` from ``urllib.parse`` (Python 3) or ``urlparse`` (Python 2)
  to prepare for the deprecation of ``urllib.parse.splittype``.
  Thanks to `@citrus-it <https://github.com/citrus-it>`_ and
  `@markmcclain <https://github.com/markmcclain>`_ for this fix.
  (see `#44 <https://github.com/tcalmant/jsonrpclib/pull/44>`_ and
  `#45 <https://github.com/tcalmant/jsonrpclib/pull/45>`_ for more details)
* Unix socket clients now send ``localhost`` as ``Host:`` HTTP field instead of
  the path to the socket
  (see `#47 <https://github.com/tcalmant/jsonrpclib/pull/47>`_).
  Thanks `@markmcclain <https://github.com/markmcclain>`_ for this fix.
* Added a ``TransportError`` exception, subclass of ``ProtocolError``, which
  provides more details
  (see `#49 <https://github.com/tcalmant/jsonrpclib/pull/49>`_).
  Thanks `@markmcclain <https://github.com/markmcclain>`_ for this improvement.
* Added PowerPC 64 architecture (``ppc64le``) to Travis CI runs, to ease the
  integration of new release into RHEL/Ubuntu (see
  `#50 <https://github.com/tcalmant/jsonrpclib/pull/50>`_ by
  `@kishorkunal-raj <https://github.com/kishorkunal-raj>`_)

0.4.1
=====

:Release Date: 2020-04-12

* Fixed a size computation issue in the request handler (see #42)


0.4.0
=====

:Release Date: 2019-01-13

* Added back support of Unix sockets on both server and client side.
  **Note:** HTTPS is not supported on server-side Unix sockets
* Fixed the CGI request handler
* Fixed the request handler wrapping on server side
* Documentation is now hosted on ReadTheDocs:
  https://jsonrpclib-pelix.readthedocs.io/


0.3.2
=====

:Release Date: 2018-10-26

* Fixed a memory leak in the Thread Pool, causing the ``PooledJSONRPCServer``
  to crash after some uptime
  (see `#35 <https://github.com/tcalmant/jsonrpclib/pull/35>`_).
  Thanks `@animalmutch <https://github.com/animalmutch>`_ for reporting it.


0.3.1
=====

:Release Date: 2017-06-27

* Hide *dunder* methods from remote calls
  (thanks to `@MarcSchmitzer <https://github.com/MarcSchmitzer>`_).
  This avoids weird behaviours with special/meta methods
  (``__len__``, ``__add__``, ...).
  See (`#32 <https://github.com/tcalmant/jsonrpclib/pull/32>`_) for reference.


0.3.0
=====

:Release Date: 2017-04-27

* Handle the potentially incomplete ``xmlrpc.server`` package when the future
  package is used
  (thanks to `@MarcSchmitzer <https://github.com/MarcSchmitzer>`_)


0.2.9
=====

:Release Date: 2016-12-12

* Added support for enumerations (``enum.Enum`` classes, added in Python 3.4)
* Removed tests for ``pypy3`` as it doesn't work with ``pip`` anymore


0.2.8
=====

:Release Date: 2016-08-23

* Clients can now connect servers using basic authentication.
  The server URL must be given using this format: http://user:password@server
* The thread pool has been updated to reflect the fixes contributed by
  `@Paltoquet <https://github.com/Paltoquet>`_ for the
  `iPOPO <https://github.com/tcalmant/ipopo>`_ project.


0.2.7
=====

:Release Date: 2016-06-12

* Application of the ``TransportMixin`` fix developped by
  `@MarcSchmitzer <https://github.com/MarcSchmitzer>`_
  (`#26 <https://github.com/tcalmant/jsonrpclib/pull/26>`_).


0.2.6
=====

:Release Date: 2015-08-24

* Removed support for Python 2.6
* Added a ``__repr__`` method to the ``_Method`` class
* Project is now tested against Python 3.4 and Pypy 3 on Travis-CI


0.2.5
=====

:Release Date: 2015-02-28

* Corrects the ``PooledJSONRPCServer``
* Stops the thread pool of the ``PooledJSONRPCServer`` in ``server_close()``
* Corrects the ``Config.copy()`` method: it now uses a copy of local classes
  and serialization handlers instead of sharing those dictionaries.


0.2.4
=====

:Release Date: 2015-02-16

* Added a thread pool to handle requests
* Corrects the handling of reused request sockets on the server side
* Corrects the ``additional_header`` feature: now supports different headers
  for different proxies, from
  `@MarcSchmitzer <https://github.com/MarcSchmitzer>`_
* Adds a ``data`` field to error responses, from
  `@MarcSchmitzer <https://github.com/MarcSchmitzer>`_ and
  `@mbra <https://github.com/mbra>`_


0.2.3
=====

:Release Date: 2015-01-16

* Added support for a custom ``SSLContext`` on client side


0.2.2
=====

:Release Date: 2014-12-23

* Fixed support for IronPython
* Fixed Python 2.6 compatibility in tests
* Added logs on server side


0.2.1
=====

:Release Date: 2014-09-18

* Return ``None`` instead of an empty list on empty replies
* Better lookup of the custom serializer to look for


0.2.0
=====

:Release Date: 2014-08-28

* Code review
* Fixed propagation of configuration through ``jsonclass``, from
  `dawryn <https://github.com/dawryn>`_


0.1.9
=====

:Release Date: 2014-06-09

* Fixed compatibility with JSON-RPC 1.0
* Propagate configuration through ``jsonclass``, from
  `dawryn <https://github.com/dawryn>`_


0.1.8
=====

:Release Date: 2014-06-05

* Enhanced support for bean inheritance


0.1.7
=====

:Release Date: 2014-06-02

* Enhanced support of custom objects (with ``__slots__`` and handlers), from
  `dawryn <https://github.com/dawryn>`_
  See Pull requests
  `#5 <https://github.com/tcalmant/jsonrpclib/pull/5>`_,
  `#6 <https://github.com/tcalmant/jsonrpclib/pull/6>`_,
  `#7 <https://github.com/tcalmant/jsonrpclib/pull/7>`_)
* Added tests
* First upload as a Wheel file


0.1.6.1
=======

:Release Date: 2013-10-25


* Fixed loading of recursive bean fields (beans can contain other beans)
* ``ServerProxy`` can now be closed using: ``client("close")()``


0.1.6
=====

:Release Date: 2013-10-14

* Fixed bean marshalling
* Added support for ``set`` and ``frozenset`` values
* Changed configuration singleton to ``Config`` instances


0.1.5
=====

:Release Date: 2013-06-20

* Requests with ID 0 are not considered notifications anymore
* Fixed memory leak due to keeping history in ``ServerProxy``
* ``Content-Type`` can be configured
* Better feeding of the JSON parser (avoid missing parts of a multi-bytes
  character)
* Code formatting/compatibility enhancements
* Applied enhancements found on other forks:

  * Less strict error response handling from
    `drdaeman <https://github.com/drdaeman/jsonrpclib>`_
  * In case of a non-predefined error, raise an ``AppError`` and give access
    to *error.data*, from
    `tuomassalo <https://github.com/tuomassalo/jsonrpclib>`_


0.1.4
=====

:Release Date: 2013-05-22

* First published version of this fork, with support for Python 3
* Version number was following the original project one
