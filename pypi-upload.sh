#!/bin/bash
set -e

echo "=== Building all artifacts ==="
./build-artifacts.sh

echo
echo "=== Running pre-release self-check ==="
python3 pre_release_check.py
if [ $? -ne 0 ]; then
    echo "Pre-release check failed. Aborting upload."
    exit 1
fi

echo
echo "=== Uploading to PyPI ==="
twine upload dist/*
