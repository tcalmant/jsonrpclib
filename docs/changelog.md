# Release Notes

## 1.0

:Release Date: 2025-11-09

- Disable CGI on Python 3.15 (see [#64](https://github.com/tcalmant/jsonrpclib/issues/64)).
  Python 3.15 will drop support for CGI, removing the parent classes we relied onto.
  Thanks [@mtelka](https://github.com/mtelka) for spotting this.
- GitHub CI configuration now runs tests from Python 3.8 to 3.15 (alpha).
  The code is manually tested on Python 2.7 and 3.6 Docker containers before releases.
- Bumping version to 1.0 as we didn't have big issues for a while and we can consider
  the project stable.

## 0.4.3.4

:Release Date: 2025-03-03

- Add `orjson` support (see [#62](https://github.com/tcalmant/jsonrpclib/pull/62)).
  Thanks [@fhaeuser](https://github.com/fhaeuser) for this.
- Updated GitHub CI configuration to support testing from Python 3.6 to 3.14.

## 0.4.3.3

:Release Date: 2024-06-14

- Added support for `decimal.Decimal` objects (see [#60](https://github.com/tcalmant/jsonrpclib/pull/60)).
  Thanks [@pourhouse](https://github.com/pourhouse) for this improvement.

## 0.4.3.2

:Release Date: 2022-02-19

- Reordered `PooledJSONRPCServer` inheritance definition ([#55](https://github.com/tcalmant/jsonrpclib/issues/55))
- Migration of Continuous Integration:

  - Use PyTest instead of Nose
  - Run CI with GitHub Actions instead of Travis-CI

## 0.4.3.2

:Release Date: 2021-09-28

- Removed remaining print statements ([#52](https://github.com/tcalmant/jsonrpclib/issues/52))

## 0.4.3

:Release Date: 2021-09-26

- `ServerProxy` keeps the given query string, as before 0.4.2.
  This release fixes [#51](https://github.com/tcalmant/jsonrpclib/issues/51),
  and a unit test has been added to ensure there won't be any regression again on this feature
- JSON library selection is now made in the `jsonrpclib.jsonlib` module,
  using a set of handler classes. This will ease the addition of new libraries.
- Added support for ujson
- Fixed Travis-CI builds (migrated from .org to .com and bypassed the coveralls issue with ppc64le)
- Fixed an issue with the CGI test in Python 3-only environments

## 0.4.2

:Release Date: 2020-11-09

- Use `urlparse` from `urllib.parse` (Python 3) or `urlparse` (Python 2)
  to prepare for the deprecation of `urllib.parse.splittype`.
  Thanks to [@citrus-it](https://github.com/citrus-it) and
  [@markmcclain](https://github.com/markmcclain) for this fix.
  (see [#44](https://github.com/tcalmant/jsonrpclib/pull/44) and
  [#45](https://github.com/tcalmant/jsonrpclib/pull/45) for more details)
- Unix socket clients now send `localhost` as `Host:` HTTP field instead of
  the path to the socket (see [#47](https://github.com/tcalmant/jsonrpclib/pull/47)).
  Thanks [@markmcclain](https://github.com/markmcclain) for this fix.
- Added a `TransportError` exception, subclass of `ProtocolError`, which
  provides more details (see [#49](https://github.com/tcalmant/jsonrpclib/pull/49)).
  Thanks [@markmcclain](https://github.com/markmcclain) for this improvement.

## 0.4.1

:Release Date: 2020-04-12

- Fixed a size computation issue in the request handler (see #42)

## 0.4.0

:Release Date: 2019-01-13

- Added back support of Unix sockets on both server and client side.
  **Note:** HTTPS is not supported on server-side Unix sockets
- Fixed the CGI request handler
- Fixed the request handler wrapping on server side
- Documentation is now hosted on ReadTheDocs: <https://jsonrpclib-pelix.readthedocs.io/>

## 0.3.2

:Release Date: 2018-10-26

- Fixed a memory leak in the Thread Pool, causing the `PooledJSONRPCServer`
to crash after some uptime (see [#35](https://github.com/tcalmant/jsonrpclib/pull/35)).
Thanks [@animalmutch](https://github.com/animalmutch) for reporting it.


## 0.3.1

:Release Date: 2017-06-27

- Hide *dunder* methods from remote calls (thanks to [@MarcSchmitzer](https://github.com/MarcSchmitzer)).
This avoids weird behaviours with special/meta methods (`__len__`, `__add__`, ...).
See [#32](https://github.com/tcalmant/jsonrpclib/pull/32) for reference.


## 0.3.0

:Release Date: 2017-04-27

- Handle the potentially incomplete `xmlrpc.server` package when the `future`
package is used (thanks to [@MarcSchmitzer](https://github.com/MarcSchmitzer)).


## 0.2.9

:Release Date: 2016-12-12

- Added support for enumerations (`enum.Enum` classes, added in Python 3.4).
- Removed tests for `pypy3` as it doesn't work with `pip` anymore.


## 0.2.8

:Release Date: 2016-08-23

- Clients can now connect servers using basic authentication. The server URL must be given using this format: `http://user:password@server`.
- The thread pool has been updated to reflect the fixes contributed by
[@Paltoquet](https://github.com/Paltoquet) for the
[iPOPO](https://github.com/tcalmant/ipopo) project.


## 0.2.7

:Release Date: 2016-06-12

- Application of the `TransportMixin` fix developed by [@MarcSchmitzer](https://github.com/MarcSchmitzer) ([#26](https://github.com/tcalmant/jsonrpclib/pull/26)).


## 0.2.6

:Release Date: 2015-08-24

- Removed support for Python 2.6.
- Added a `__repr__` method to the `_Method` class.
- Project is now tested against Python 3.4 and Pypy 3 on Travis-CI.


## 0.2.5

:Release Date: 2015-02-28

- Corrects the `PooledJSONRPCServer`.
- Stops the thread pool of the `PooledJSONRPCServer` in `server_close()`.
- Corrects the `Config.copy()` method: it now uses a copy of local classes
and serialization handlers instead of sharing those dictionaries.


## 0.2.4

:Release Date: 2015-02-16

- Added a thread pool to handle requests.
- Corrects the handling of reused request sockets on the server side.
- Corrects the `additional_header` feature: now supports different headers
for different proxies (thanks to [@MarcSchmitzer](https://github.com/MarcSchmitzer)).
- Adds a `data` field to error responses (thanks to [@MarcSchmitzer](https://github.com/MarcSchmitzer) and [@mbra](https://github.com/mbra)).


## 0.2.3

:Release Date: 2015-01-16

- Added support for a custom `SSLContext` on client side.


## 0.2.2

:Release Date: 2014-12-23

- Fixed support for IronPython.
- Fixed Python 2.6 compatibility in tests.
- Added logs on server side.


## 0.2.1

:Release Date: 2014-09-18

- Return `None` instead of an empty list on empty replies.
- Better lookup of the custom serializer to look for.


## 0.2.0

:Release Date: 2014-08-28

- Code review.
- Fixed propagation of configuration through `jsonclass` (thanks to [@dawryn](https://github.com/dawryn)).


## 0.1.9

:Release Date: 2014-06-09

- Fixed compatibility with JSON-RPC 1.0.
- Propagate configuration through `jsonclass` (thanks to [@dawryn](https://github.com/dawryn)).


## 0.1.8

:Release Date: 2014-06-05

- Enhanced support for bean inheritance.


## 0.1.7

:Release Date: 2014-06-02

- Enhanced support of custom objects (with `__slots__` and handlers), from
[@dawryn](https://github.com/dawryn).
See Pull requests [#5](https://github.com/tcalmant/jsonrpclib/pull/5),
[#6](https://github.com/tcalmant/jsonrpclib/pull/6),
[#7](https://github.com/tcalmant/jsonrpclib/pull/7).
- Added tests.
- First upload as a Wheel file.


## 0.1.6.1

:Release Date: 2013-10-25

- Fixed loading of recursive bean fields (beans can contain other beans).
- `ServerProxy` can now be closed using: `client("close")()`.


## 0.1.6

:Release Date: 2013-10-14

- Fixed bean marshalling.
- Added support for `set` and `frozenset` values.
- Changed configuration singleton to `Config` instances.


## 0.1.5

:Release Date: 2013-06-20

- Requests with ID 0 are not considered notifications anymore.
- Fixed memory leak due to keeping history in `ServerProxy`.
- `Content-Type` can be configured.
- Better feeding of the JSON parser (avoid missing parts of a multi-bytes
character).
- Code formatting/compatibility enhancements.
- Applied enhancements found on other forks:

- Less strict error response handling from [drdaeman](https://github.com/drdaeman/jsonrpclib).
- In case of a non-predefined error, raise an `AppError` and give access
    to `error.data`, from [tuomassalo](https://github.com/tuomassalo/jsonrpclib).


## 0.1.4

:Release Date: 2013-05-22

- First published version of this fork, with support for Python 3.
- Version number was following the original project one
