#!/bin/bash
# Upload jc package to PyPI.
# Verifies documentation consistency before uploading.
# Requires twine: pip install twine

set -euo pipefail
cd "$(dirname "$0")"

echo "=== Pre-upload: verifying documentation consistency ==="
python3 pre_release_check.py

echo "=== Uploading to PyPI ==="
twine upload dist/*