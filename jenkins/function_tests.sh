#!/usr/bin/env bash
set -e
echo "Exporting username"
export USER=`whoami`
echo "Making sure all requirements are installed"
pip3 --no-cache-dir install -r requirements.txt

echo "Entering tests folder"
cd tests/function_tests
echo "Setting PYTHONPATH"
export PYTHONPATH=$PYTHONPATH:../../
echo "Launching tests"
python36 -m pytest --verbose --junit-xml "../../test-reports/${STAGE_NAME}.xml" test_main.py

