# How to contribute

Contributions to `jsonrpclib-pelix` are welcome, whether they are bug reports,
documentation, tests or code.

## Issues & feedback

Bugs and feature requests belong on the
[GitHub issue tracker](https://github.com/tcalmant/jsonrpclib/issues). For
security issues, follow [`SECURITY.md`](SECURITY.md) instead: **do not** open a
public issue.

## Code contributions

Fork the project and open a
[pull request](https://github.com/tcalmant/jsonrpclib/pulls) against `main`.
Your code will be reviewed, tested and merged. Contributions must be released
under the project's license, the
[Apache Software License 2.0](https://www.apache.org/licenses/LICENSE-2.0).

If you don't write documentation or tests, the maintainer may write some; but
contributing both increases the chance your pull request is accepted quickly.

## The one rule that shapes everything: Python 2.7 still works

The 1.x line **must keep running on Python 2.7** as well as 3.6+. This single
constraint dictates most of the style below. When in doubt, assume the code will
be imported by a Python 2.7 interpreter.

Concretely, on the 1.x line **do not**:

- use f-strings: use `"{0}".format(...)`;
- add function/variable annotations in `jsonrpclib/`: use `# type:` comments
  (the one exception is `tests/test_pydantic.py`, which is annotation-based and
  is skipped on 2.7);
- use `super().__init__()`: call the base explicitly,
  `BaseClass.__init__(self, ...)`;
- drop `class Foo(object)` base classes (they matter for 2.7 old-style classes);
- remove the `try: <py3 import> / except ImportError: <py2 import>` shims or the
  `jsonrpclib/utils.py` type aliases;
- assume any of `enum`, `decimal`, `gzip`, `fcntl`, `socket.AF_UNIX` or
  `pydantic` is present: they are all optional and guarded.

If a change genuinely cannot be made 2.7-compatible, it belongs on the future
2.x line, not here. Say so in the pull request.

## Code style

- Follow [PEP 8](https://peps.python.org/pep-0008/).
- An [EditorConfig](https://editorconfig.org/) is provided.
- **Break lines after 80 characters** (`black` and `ruff` are configured for
  80 in `pyproject.toml`). URLs may exceed it.
- Format with [`black`](https://black.readthedocs.io/); it needs no arguments.
- Use `logging`, never `print`, for diagnostics.
- Remove unused imports (the intentional re-exports in `jsonrpclib/__init__.py`
  carry an explicit `# noqa: F401`).
- Use `CamelCase` for classes, `snake_case` for functions/methods,
  `SNAKE_UPPERCASE` for constants.
- Every module carries the standard docstring header (authors, copyright,
  license, `:version:`) and a `__version_info__` tuple. Keep them present.

## Running the tests

The full suite exercises the library against each JSON backend in turn
(`orjson`, `ujson`, `cjson`, `simplejson`, stdlib `json`), installing and
uninstalling each. This is what CI runs:

```bash
./run_tests.sh
# or, in an isolated virtual environment:
uv run ./run_tests.sh
```

For a quick run against your current interpreter:

```bash
pytest tests
python -m unittest discover tests
```

The `tests/test_jsonlib.py` cases only assert something when
`JSONRPCLIB_TEST_EXPECTED_LIB` names the backend that should win the selection;
`run_tests.sh` sets it for you. On Python 2.7, `tests/test_pydantic.py` raises a
`SyntaxError` on import and must be ignored (`--ignore tests/test_pydantic.py`).

To run `./run_tests.sh` on every supported Python version — including 2.7 and
3.6, which are outside the GitHub Actions matrix — use the container runner
(needs `podman` or `docker`):

```bash
./run_tests_containers.sh              # all supported versions
./run_tests_containers.sh 2.7 3.6      # only these
```

It streams a clean copy of the tree into an official `python:<version>` image
and reports a pass/fail summary, without touching your working copy.

Before opening a pull request:

```bash
black --check . && ruff check .
python .github/scripts/check_version.py
./run_tests.sh
```

## Documentation

Documentation lives in `docs/` and is built with
[Sphinx](https://www.sphinx-doc.org/) and [MyST](https://myst-parser.readthedocs.io/)
(Markdown). User-visible changes get an entry in `docs/changelog.md`; security
fixes go in a `### Security` subsection of the release they ship in.

## Releasing

Releases are made by the maintainer; the steps are written down so they are
reproducible.

1. **Bump the version.** It is declared in `pyproject.toml` and, in every module
   of `jsonrpclib`, both as `__version_info__` and as the `:version:` docstring
   field. Also update `docs/conf.py`. All of them must agree:

   ```bash
   python .github/scripts/check_version.py
   ```

2. **Set the release date** in `docs/changelog.md`, replacing `Unreleased` for
   the section being released. That section is the source of the release notes,
   so it must describe the release completely.

3. **Check the branch locally**, as CI does:

   ```bash
   black --check . && ruff check .
   python .github/scripts/check_version.py
   ./run_tests.sh
   ```

4. Additionally, before a release, run the suite on **every supported Python
   version**, including the **2.7 and 3.6** that CI does not cover:

   ```bash
   ./run_tests_containers.sh
   ```

5. **Tag and push.** Tags are annotated and signed:

   ```bash
   git tag -s X.Y.Z -m "vX.Y.Z"
   git push origin X.Y.Z
   ```

   The publication (build, upload to PyPI, GitHub release) then runs from CI see `.github/workflows/`.
