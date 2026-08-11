# Installation

## Requirements

This library runs on Python 2.7 and Python 3.6+.
The test suite is run on every supported version (2.7, then 3.6 to 3.15) in
GitHub CI, using the matching `python:<version>` container.

No third-party package is required: the built-in `json` module is used by
default.
The library can also use `orjson`, `ujson`, `simplejson` and `cjson` if they
are installed, and looks for the parsers in that order (`orjson`, `ujson`,
`simplejson`, `cjson`, then the built-in `json`).
Each candidate is validated with a round-trip before being used, so a parser
which is installed but broken is skipped.
Keep in mind that `orjson` is supposed to be the quickest, so for full-on
optimization you may want to pick it up.

## Installation

You can install the latest stable version from PyPI with the following command:

```console
# Global installation
pip install jsonrpclib-pelix

# Local installation
pip install --user jsonrpclib-pelix
```

Alternatively, you can install the latest development version:

```console
pip install git+https://github.com/tcalmant/jsonrpclib.git
```

Finally, you can download the source from the GitHub repository
at <https://github.com/tcalmant/jsonrpclib> and manually install it
with the following commands:

```console
git clone https://github.com/tcalmant/jsonrpclib.git
cd jsonrpclib
pip install .
```

On Python 2.7, where `pip` might be too old to handle the project metadata, use
`python setup.py install` instead.

## Tests

Tests are an almost-verbatim drop from the JSON-RPC specification 2.0 page.

You can also run the test script, `./run_tests.sh` that will also try
to install then remove the optional JSON parsing libraries (`orJson`, `uJson`, ...).
This is the script executed by GitHub CI and in Docker containers before releases.

The script can also be executed with `uv` to use a virtual environment to run tests:
`uv run ./run_tests.sh`.

You can also run tests for your setup using `unittest` or `pytest`:

```console
python -m unittest discover tests
python3 -m unittest discover tests
pytest tests
```
