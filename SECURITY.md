# Security Policy

`jsonrpclib-pelix` is a JSON-RPC 1.0/2.0 client and server library. The server
side (`SimpleJSONRPCServer`, `PooledJSONRPCServer`, the CGI handler) is
network-facing and, by design, unauthenticated. Security reports are taken
seriously and are welcome.

## Supported versions

| Version | Branch | Python | Status |
| ------- | ------ | ------ | ------ |
| 1.x     | `main` | 2.7, 3.6+ | Actively maintained: security and bug fixes |
| < 1.0   | —      | 2.7, 3.x  | Unsupported: please upgrade |

The 1.x line deliberately keeps **Python 2.7** working, because instances are
still deployed on it. Fixes on 1.x therefore stay 2.7-compatible.

A future 2.x line will require a modern Python (3.11+). When it exists, 1.x will
continue to receive security fixes for the deployed-on-2.7 users, and this table
will be updated with the exact support window.

Only the latest release of a supported line receives fixes. If you are running
an older patch release, upgrade before reporting an issue.

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub issues,
pull requests or discussions.**

### Preferred: GitHub private vulnerability reporting

Report via the repository's **Security** tab → **Report a vulnerability**:

> https://github.com/tcalmant/jsonrpclib/security/advisories/new

This creates a private advisory visible only to you and the maintainers, allows
coordinated disclosure, and can be used to request a CVE identifier once the
report is confirmed.

### Alternative: email

If you cannot use GitHub, email **thomas.calmant+github@gmail.com**. If you wish
to encrypt your report, request the maintainer's public key at that address
before sending details.

### What to include

- **Affected version** (e.g. `1.1.0`) and the Python version
- **Type of issue**: remote code execution, unsafe deserialization, denial of
  service, information disclosure, etc.
- **Reproduction steps**, ideally a minimal script. A failing test case is ideal
- **Impact assessment**: what an attacker gains, and what access they need
  (reachable TCP port, ability to send a crafted response to a client, …)
- **Any suggested mitigation or patch**, if you have one

Reports written in English or French are both fine.

## What to expect

| Stage | Target |
| ----- | ------ |
| Acknowledgement of your report | within **5 business days** |
| Initial assessment | within **10 business days** |
| Fix for critical/high severity issues | within **30 days** of confirmation |
| Fix for medium/low severity issues | next scheduled release |

This is a volunteer-maintained project; these are the targets aimed for, not a
contractual guarantee. If a fix will take longer, you will be told, and why.

## Disclosure policy

Coordinated disclosure is followed: you report privately, the report is
confirmed and a fix is developed in private with you kept in the loop, a release
containing the fix is published together with a GitHub Security Advisory and a
changelog entry, and public disclosure happens **after** the fixed release is
available (normally within **90 days** of the initial report). If a
vulnerability is already public or exploited in the wild, the timeline is
compressed and mitigation guidance is published as quickly as possible.

Reporters are credited by name and/or handle in the advisory and changelog,
unless you ask to remain anonymous. There is no bug bounty programme.

## Scope

### In scope

- The `jsonrpclib` package as published on PyPI as `jsonrpclib-pelix`
- The documented default configuration of the client and the servers
- The build and release pipeline (`.github/workflows/`) and the integrity of
  published artifacts

### Out of scope

- **Third-party dependencies** (`orjson`, `ujson`, `simplejson`, `cjson`).
  Report those to their own maintainers. If jsonrpclib's *use* of one of them is
  what creates the vulnerability, that is in scope — please do report it
- **Application code built with the library**, unless a library API makes the
  insecure behavior unavoidable or is misleading about its guarantees
- Findings from automated scanners submitted without a demonstrated impact
- Attacks requiring an already-compromised host

### Known design limitations

These are **current, documented behaviors**. They are known; a *specific, novel*
exploitation technique against them is still worth reporting.

- **Class translation (`jsonclass`) deserializes objects from the peer.**
  When `use_jsonclass` is enabled, a `__jsonclass__` payload asks the receiver
  to instantiate a class. Restrict what may be instantiated with the
  `config.classes` registry, and only enable class translation between endpoints
  you trust. See the changelog for how the default has been hardened.
- **The servers are unauthenticated.** `SimpleJSONRPCServer` and
  `PooledJSONRPCServer` perform no authentication or authorization: any client
  that can reach the port can invoke any registered method. Expose them only on
  a trusted network or behind an authenticating reverse proxy, and prefer TLS
  (`SafeTransport` / an `ssl`-wrapped server socket)
- **No concurrency limit on the pooled server.** `PooledJSONRPCServer` handles
  each connection in a thread pool with no rate limiting. Set
  `SimpleJSONRPCRequestHandler.max_request_size` to bound request bodies, and do
  not expose the server to untrusted clients

## Hardening guidance for deployments

- **Do not enable class translation across a trust boundary.** If you must,
  populate `config.classes` so only known classes can be instantiated, and never
  rely on dynamic import against untrusted peers
- **Use TLS.** Wrap the server socket with `ssl`, and connect with `https://`
- **Bound request size.** Subclass `SimpleJSONRPCRequestHandler` and set
  `max_request_size` (see the README)
- **Keep servers on trusted networks**, or behind an authenticating proxy
- **Run as an unprivileged user**, in a container or under a restricted service
  manager
- **Watch the releases feed** (https://github.com/tcalmant/jsonrpclib/releases)
  or subscribe to repository security advisories

## Security advisories

Published advisories are listed at:

> https://github.com/tcalmant/jsonrpclib/security/advisories

Fixes are also noted in the changelog (`docs/changelog.md`) and in the release
notes.

## Questions

For questions about this policy that are **not** themselves a vulnerability
report, open a regular GitHub issue or discussion.
