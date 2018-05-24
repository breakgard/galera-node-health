#!/usr/bin/env bash

set -e
echo "-------------------Preparing image tests-----------------"
if [ ! -d 'test-reports' ];
then
    mkdir test-reports
fi
touch "test-reports/${STAGE_NAME}.xml"
echo "Entering test folder"
cd tests/image_tests
echo "Launcihng install_db.sh"
./install_db.sh
echo "install_db.sh finished"
echo "-------------------Running image tests-------------------"
python36 -m pytest --verbose --junit-xml "../../test-reports/${STAGE_NAME}.xml" test_docker_image.py
