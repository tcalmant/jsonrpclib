.. _installation:

Installation
============

Requirements
************

It supports ``orjson``, ``cjson`` and ``simplejson``, and looks for the parsers
in that order (searching first for `orjson`, `ujson`, `cjson`, `simplejson` and
finally for the *built-in* `json`).
One of these must be installed to use this library, although if you have a
standard distribution of 2.7+, you should already have one.
Keep in mind that ``orjson`` is supposed to be the quickest, I believe, so if
you are going for full-on optimization you may want to pick it up.


Installation
************

You can install the latest stable version from PyPI with the following command:

.. code-block:: console

   # Global installation
   pip install jsonrpclib-pelix

   # Local installation
   pip install --user jsonrpclib-pelix

Alternatively, you can install the latest development version:

.. code-block:: console

   pip install git+https://github.com/tcalmant/jsonrpclib.git

Finally, you can download the source from the GitHub repository
at http://github.com/tcalmant/jsonrpclib and manually install it
with the following commands:

.. code-block:: console

   git clone git://github.com/tcalmant/jsonrpclib.git
   cd jsonrpclib
   python setup.py install


Tests
*****

Tests are an almost-verbatim drop from the JSON-RPC specification 2.0 page.
They can be run using *unittest* or *nosetest*:

.. code-block:: console

   python -m unittest discover tests
   python3 -m unittest discover tests
   nosetests tests
