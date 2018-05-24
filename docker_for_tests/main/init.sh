#!/usr/bin/env bash

set -e
echo "-------------------Preparing tests-----------------"
git clone "${GIT_URL}" ~/galera_node_checker

pip3 --no-cache-dir install -r ~/galera_node_checker/requirements.txt

echo "-------------------Running tests-------------------"
export PYTHONPATH=${PYTHONPATH}:~/galera_node_checker
export USER=`whoami`
cd ~/galera_node_checker/tests/function_tests

python36 -u -m pytest test_main.py
