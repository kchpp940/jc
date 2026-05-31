#!/bin/bash
# Build all generated artifacts using the canonical gen scripts
# This is the single source of truth for artifact generation

set -e

echo "=== Building all generated artifacts ==="

echo
echo "1. Generating README.md..."
python3 readmegen.py
echo "   ✓ README.md generated"

echo
echo "2. Generating README-snap.md..."
python3 readmesnapgen.py
echo "   ✓ README-snap.md generated"

echo
echo "3. Generating man page..."
python3 mangen.py
echo "   ✓ man/jc.1 generated"

echo
echo "4. Generating shell completions..."
python3 build-completions.py
echo "   ✓ completions generated"

echo
echo "5. Generating parser documentation..."
./docgen.sh all
echo "   ✓ parser docs generated"

echo
echo "=== All artifacts built successfully ==="
