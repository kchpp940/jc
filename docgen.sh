#!/bin/bash
# Generate markdown document files (*.md)
#
# DEPRECATED: This script delegates to generate_docs.py.
# The old docgen.sh behavior (parallel + incremental) is replaced by
# a sequential full-generation pass that guarantees consistency.

cd "$(dirname "$0")"

python3 generate_docs.py "$@"
