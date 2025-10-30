#!/bin/bash
#
# Script to execute tests in Docker / CI / UV environment
#

if [ -z "$UV" ]
then
    echo "UV is not set"
else
    echo "Using UV at $UV"
fi

run_pip_install() {
    if [ -z "$UV" ]
    then
        pip install "$@"
        return $?
    else
        uv pip install "$@"
        return $?
    fi
}

run_pip_uninstall() {
    if [ -z "$UV" ]
    then
        pip uninstall -y "$@"
        return $?
    else
        uv pip uninstall "$@"
        return $?
    fi
}

run_coverage() {
    if [ -z "$UV" ]
    then
        coverage "$@"
        return $?
    else
        uv run coverage "$@"
        return $?
    fi
}

run_lib_tests() {
    export JSONRPCLIB_TEST_EXPECTED_LIB="$1"
    run_pip_install "$2"
    if [ $? -ne 0 ]
    then
        echo "Failed to install $2"
        return 0
    fi

    run_coverage run -m pytest tests/test_jsonlib.py
    rc=$?
    run_pip_uninstall "$2"
    return $rc
}

echo "Installing dependencies..."
run_pip_install pytest coverage || exit 1
export COVERAGE_PROCESS_START=".coveragerc"

echo "Initial tests..."
export JSONRPCLIB_TEST_EXPECTED_LIB=json
run_coverage run -m pytest || exit 1

echo "orJson tests..."
run_lib_tests orjson orjson || exit 1

echo "uJson tests..."
run_lib_tests ujson ujson || exit 1

echo "cJson tests..."
run_lib_tests cjson python-cjson || exit 1

echo "simplejson tests..."
run_lib_tests simplejson simplejson || exit 1

echo "Combine results..."
run_coverage combine || exit $?
run_coverage report
