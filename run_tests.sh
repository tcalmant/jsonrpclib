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

run_python() {
    if [ -z "$UV" ]
    then
        python "$@"
        return $?
    else
        uv run python "$@"
        return $?
    fi
}

# test_pydantic.py uses type annotations, so it cannot even be imported on
# Python 2 (SyntaxError). On Python 3 it self-skips when Pydantic is missing,
# so it is always safe to collect there.
python_is_py3() {
    run_python -c 'import sys; sys.exit(0 if sys.version_info[0] >= 3 else 1)' \
        >/dev/null 2>&1
}

# cjson and simplejson are only tested before Python 3.15 (see the changelog).
python_before_3_15() {
    run_python \
        -c 'import sys; sys.exit(0 if sys.version_info[:2] < (3, 15) else 1)' \
        >/dev/null 2>&1
}

echo "Installing dependencies..."
run_pip_install pytest coverage || exit 1
export COVERAGE_PROCESS_START=".coveragerc"

if python_is_py3
then
    echo "Trying to install Pydantic for its tests..."
    if run_pip_install pydantic
    then
        echo "Pydantic installed: including its tests"
    else
        echo "Pydantic unavailable here: its tests will self-skip"
    fi
    EXTRA_ARGS=()
else
    echo "Python 2: ignoring the Pydantic tests (they use annotations)"
    EXTRA_ARGS=("--ignore" "tests/test_pydantic.py")
fi

echo "Initial tests..."
export JSONRPCLIB_TEST_EXPECTED_LIB=json
run_coverage run -m pytest "${EXTRA_ARGS[@]}" || exit 1

echo "orJson tests..."
run_lib_tests orjson orjson || exit 1

echo "uJson tests..."
run_lib_tests ujson ujson || exit 1

if python_before_3_15
then
    echo "cJson tests..."
    run_lib_tests cjson python-cjson || exit 1

    echo "simplejson tests..."
    run_lib_tests simplejson simplejson || exit 1
else
    echo "Ignoring cjson and simplejson tests: Python 3.15+ is not supported."
fi


echo "Combine results..."
run_coverage combine || exit $?
run_coverage report
