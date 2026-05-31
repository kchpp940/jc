#!/bin/bash
# build jc PIP package
# to install locally, run:   pip3 install jc-x.x.tar.gz

set -e

echo "=== Building all artifacts ==="
./build-artifacts.sh

echo
echo "=== Running pre-release self-check ==="
python3 pre_release_check.py
if [ $? -ne 0 ]; then
    echo "Pre-release check failed. Aborting build."
    exit 1
fi

echo
echo "=== Building PIP package ==="
python3 setup.py sdist bdist_wheel
