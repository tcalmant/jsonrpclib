# Release Notes

## 1.2

:Release Date: Unreleased

### Security

- Class translation (`jsonclass`) no longer imports arbitrary classes by
  default. A `__jsonclass__` payload could previously make a server or client
  instantiate any importable class with attacker-controlled arguments, when
  `use_jsonclass` was enabled (the default) and no class registry was set.
  Dynamic import is now opt-in through the new `Config.allow_dynamic_classes`
  flag (default `False`); unregistered classes are refused with a
  `TranslationError`. Restrict what may be instantiated with `Config.classes`,
  and only enable class translation between endpoints you trust.

  **This changes the default behaviour:** classes must now be declared with
  `config.classes.add()` on **both** ends, including the enumerations and the
  Pydantic models which used to be rebuilt implicitly. Only `decimal.Decimal`
  is always accepted, as a value type the library serializes itself. Setting
  `Config(allow_dynamic_classes=True)` restores the previous behaviour.

- `register_instance()` no longer accepts dotted method names by default. The
  `allow_dotted_names` argument of `register_instance()` was ignored: method
  names were always resolved by walking the attributes of the registered
  instance, so a client could reach any object it holds a reference to — and
  therefore any callable on it. `SimpleXMLRPCServer`, which this library
  mirrors, has always required this to be requested explicitly.

  **This changes the default behaviour:** a server registering an instance now
  answers `-32601` (method not supported) to `a.b.c` style names. If you rely
  on them, and the registered instance holds nothing a caller should not reach,
  ask for them as you would with `xmlrpclib`:
  `server.register_instance(obj, allow_dotted_names=True)`. Attributes whose
  name starts with `_` remain unreachable either way.

- Server-side exceptions are no longer described in the errors sent to the
  peer. A failing method used to answer with a fragment of its traceback — the
  source file, the line, the function name and the exception message — which
  any caller could read. Such an error is now reported as
  `Server error (ref: <id>)`, and the same reference is written to the logs
  along with the whole traceback, so the details can still be looked up.

  The errors describing what the *caller* sent are unchanged: an unknown
  method, invalid parameters or an unparsable request are still explicit, as
  they are meant to be acted upon.

  Set `Config(send_exception_details=True)` to get the previous behaviour back
  while developing. Do not enable it on a server which is reachable by
  untrusted callers.

### Fixed

- `ServerProxy._additional_headers` no longer leaks headers when the wrapped
  call raises: the additional headers are now always removed from the transport
  when leaving the `with` block.

- Requests with a `Content-Encoding: gzip` body are handled again. The body was
  converted to text chunk by chunk before being decompressed, so
  `gzip_decode()` never got the bytes it expects and the server answered an
  `HTTP 500`. The chunks are now joined and decompressed before being read as
  text. The client of this library is unaffected: it never compressed the
  requests it sends.

  The same change fixes a body larger than 10 MiB being rejected when a chunk
  boundary fell in the middle of a multi-byte character (Python 3 only).
  `SimpleJSONRPCRequestHandler.max_chunk_size` is now a class attribute, next
  to `max_request_size`.

- Interrupting a server with `Ctrl-C` while it is serving a call no longer
  turns the `KeyboardInterrupt` into a JSON-RPC error. The three handlers which
  caught every exception (`SimpleJSONRPCDispatcher._dispatch`,
  `SimpleJSONRPCRequestHandler.do_POST` and `TransportMixIn.single_request`)
  now let `KeyboardInterrupt` and `SystemExit` through, as `xmlrpc.client`
  does, so they reach the server loop. A method raising `SystemExit` stops the
  server instead of answering a `-32603` error.

- An invalid request is no longer quoted back in full. The errors reporting an
  unparsable request (`-32700`) or one without a version marker (`-32600`)
  embedded the whole request, so a 20 kB body produced a 20 kB answer and a
  20 kB log line, both chosen by the caller. Only the first
  `SimpleJSONRPCServer.MAX_ECHOED_REQUEST_SIZE` characters (256 by default) are
  quoted now, followed by the total length. What was wrong with the request is
  still reported.

- Requests are now checked for a usable framing before anything is read from
  them. A request without a `Content-Length` is answered with an `HTTP 411`
  (`Length Required`) and one with an unusable value with an `HTTP 400`
  (`Bad Request`), where both used to raise inside the request handler and be
  reported as an `HTTP 500` describing the server. Oversized requests are still
  refused with an `HTTP 413` before the body is read.

  Note that `max_request_size` is compared to the `Content-Length` header: it
  bounds what is read from the socket, not what the body expands to once
  decoded.

### Documentation

- Documented that a `ServerProxy` must not be shared between threads. Its
  transport keeps a single connection, and its additional headers live in a
  list shared by every caller: a request sent while another thread is inside a
  `_additional_headers` block carries that block's headers, credentials
  included. See the "Thread safety" section of the client documentation.

- The SSL server snippet no longer uses `ssl.wrap_socket()`, which was removed
  in Python 3.12: it now uses an `ssl.SSLContext`. The client side of TLS (the
  `context` argument of `ServerProxy`) is documented as well.
- The class translation examples now declare their classes in the registry, as
  required since this release.
- Fixed the description of the JSON parser lookup order (`orjson`, `ujson`,
  `simplejson`, `cjson`, then the built-in `json`) and the claim that one of
  the third-party parsers had to be installed: the built-in `json` module is
  enough. The supported and tested Python versions (2.7, then 3.6 to 3.15) are
  now stated explicitly.
- Fixed the source installation instructions: the `git://` protocol has been
  disabled by GitHub, and `pip install .` replaces `python setup.py install`
  outside of Python 2.7. Dropped the mentions of `nosetests`.
- The class translation page no longer claims the feature is turned off by
  default, which contradicted both the code and the rest of the page.

### Project

- Distributions are now built as a universal `py2.py3-none-any` wheel again, so
  Python 2.7 users can install from a wheel. The build backend moved to
  setuptools and `requires-python` was corrected to include 2.7.
- `python setup.py install` works again on Python 2.7 (metadata is provided
  explicitly there, since its setuptools predates `pyproject.toml` metadata).
- Added a `SECURITY.md` (supported versions and how to report a vulnerability),
  a `CONTRIBUTING.md` and a Dependabot configuration.
- Releases are now built and published by a `Publish` GitHub Actions workflow,
  triggered by a signed tag, using PyPI Trusted Publishing (no stored token),
  with a SLSA build provenance attestation, a CycloneDX SBOM and PEP 740
  attestations on each artifact. The release notes are generated from this
  changelog.
- Continuous integration now checks that the version is declared consistently
  across the modules and `pyproject.toml`, and enforces `ruff` (a Python
  2.7-safe rule set) and `black`.
- Added `run_tests_containers.sh` to run the test suite in containers across
  every supported Python version, including 2.7 and 3.6. Continuous integration
  now uses it to test the whole supported matrix (2.7 through 3.15), instead of
  only the versions the runner can install directly.
- Coverage is now computed from every version of the test matrix instead of a
  single interpreter: each container exports its coverage data
  (`COVERAGE_OUTPUT_DIR`), and a final job combines them all before reporting to
  Coveralls. This covers the version-specific branches, starting with the Python
  2.7 half of `utils.py`. Removed the stale `.coveralls.yml`, which still
  declared Travis CI as the service.

## 1.1

:Release Date: 2026-05-30

- Fixed access to error message in results
- Allow the request query ID to be set to 0 or empty string
- Allow the definition of a classes registry to restrict dynamic imports
- Allow the definition of a maximum content length to reject large requests
- Overall code review
- Disable `cjson` and `simplejson` tests on Python 3.15

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
