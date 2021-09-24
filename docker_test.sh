#!/bin/bash
#
# Script to execute tests in Docker
#

echo "Installing dependencies..."
pip install nose coverage || exit 1
export COVERAGE_PROCESS_START=".coveragerc"

echo "Initial tests..."
export JSONRPCLIB_TEST_EXPECTED_LIB=json
nosetests -v --exe --with-coverage --cover-package=jsonrpclib tests || exit 1

echo "uJson tests..."
pip install ujson && (
    export JSONRPCLIB_TEST_EXPECTED_LIB=ujson
    nosetests -v --with-coverage --cover-package=jsonrpclib tests/test_jsonlib.py || exit 1
    pip uninstall -y ujson
)

echo "cJson tests..."
pip install python-cjson && (
    export JSONRPCLIB_TEST_EXPECTED_LIB=cjson
    nosetests -v --with-coverage --cover-package=jsonrpclib tests/test_jsonlib.py || exit 1
    pip uninstall -y python-cjson
)

echo "simplejson tests..."
pip install simplejson && (
    export JSONRPCLIB_TEST_EXPECTED_LIB=simplejson
    nosetests -v --with-coverage --cover-package=jsonrpclib tests/test_jsonlib.py || exit 1
    pip uninstall -y simplejson
)
