#!/usr/bin/env bash

set -e
echo "-------------------Preparing tests-----------------"
git clone "${GIT_URL}" ~/galera_node_checker
cd ~/galera_node_checker/tests/image_tests
./install_db.sh

echo "-------------------Running tests-------------------"
python36 -u -m pytest test_docker_image.py