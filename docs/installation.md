# Installation

## Requirements

It supports `orjson`, `cjson` and `simplejson`, and looks for the parsers
in that order (searching first for `orjson`, `ujson`, `cjson`, `simplejson` and
finally for the built-in `json`).
One of these must be installed to use this library, although if you have a
standard distribution of Python 2.7+ or 3.x, you should already have one.
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
git clone git://github.com/tcalmant/jsonrpclib.git
cd jsonrpclib
python setup.py install
```

## Tests

Tests are an almost-verbatim drop from the JSON-RPC specification 2.0 page.

You can also run the test script, `./run_tests.sh` that will also try
to install then remove the optional JSON parsing libraries (`orJson`, `uJson`, ...).
This is the script executed by GitHub CI and in Docker containers before releases.

The script can also be executed with `uv` to use a virtual environment to run tests:
`uv run ./run_tests.sh`.

You can also run tests for your setup using `unittest`, `nosetest` or `pytest`:

```console
python -m unittest discover tests
python3 -m unittest discover tests
nosetests tests
pytest tests
```
