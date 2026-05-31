#!/bin/bash
# Build jc PIP package.
# Regenerates documentation and verifies consistency before building.
# To install locally, run:   pip3 install jc-x.x.tar.gz

set -euo pipefail
cd "$(dirname "$0")"

echo "=== Pre-build: verifying documentation consistency ==="
python3 pre_release_check.py

echo "=== Pre-build: regenerating documentation ==="
python3 generate_docs.py

echo "=== Building package ==="
python3 setup.py sdist bdist_wheel
