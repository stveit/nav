#!/bin/bash -xe

# MAIN EXECUTION POINT
cd "$WORKSPACE"
#tox -e integration-py38-django32 -- tests/unittests/general/web_middleware_test.py
tox -e integration-py38-django32 -- tests/integration/web

# Code analysis steps
#tox -e pylint
#/count-lines-of-code.sh

echo "test.sh done"
