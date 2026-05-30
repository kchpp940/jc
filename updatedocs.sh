#!/bin/bash
# Update all documentation (README.md, Man page, Doc files)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run documentation integrity check
# Full report shown for awareness, but only new/changed parser gaps block the build
echo "=== Running Documentation Integrity Check ==="
python3 "${SCRIPT_DIR}/doccheck.py"
echo "=== Documentation Check Complete ==="
echo "Note: Historical gaps are shown for awareness but do not block doc generation."
echo "      Only new/changed parser gaps block 'docgen.sh --strict'."
echo "      Use './doccheck.py --new --verbose' to check only new/changed parsers."
echo

(
    echo === Building README.md
    ./readmegen.py && echo "++++ README.md build successful" || echo "---- README.md build failed"
) &

(
    echo === Building man page
    ./mangen.py && echo "++++ man page build successful" || echo "---- man page build failed"
) &

(
    echo === Building documentation
    ./docgen.sh && echo "++++ documentation build successful" || echo "---- documentation build failed"
) &

wait
echo
echo "All documentation updated"

echo
echo "Building shell completion scripts"
./build-completions.py && echo "++++ shell completion build successful" || echo "---- shell completion build failed"
