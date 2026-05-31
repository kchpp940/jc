#!/bin/bash
# Update all documentation (README.md, man page, parser docs, shell completions)
# Uses the unified generator to guarantee consistency.

cd "$(dirname "$0")"

python3 generate_docs.py "$@"
