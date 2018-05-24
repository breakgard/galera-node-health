#!/bin/bash
set -e

function cleanup(){

    rm -rf src

}
trap cleanup EXIT
mkdir src
cp -r ../galera_node_health ../README.md ../setup.py src/
docker build $1 $2 $3 $4
