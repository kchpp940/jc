#!/usr/bin/env python3
"""
Pre-release consistency check for jc documentation.

Verifies that every on-disk artifact matches what the current parser
metadata and docstrings would produce.  Exits 0 only when all files
are in sync; exits 1 on any drift.

Intended to be run before tagging a release:
    python pre_release_check.py
    python pre_release_check.py --diff   # also show diffs for stale files

This is a thin wrapper around ``generate_docs.generate_all_docs`` with
``check_only=True`` so nothing is written to disk.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    from generate_docs import generate_all_docs

    show_diff = '--diff' in sys.argv
    ok = generate_all_docs(check_only=True, show_diff=show_diff)

    if ok:
        print("Pre-release check PASSED: all documentation is consistent.")
    else:
        print("Pre-release check FAILED: documentation is out of sync with parser metadata.")
        print("Run `python generate_docs.py` to regenerate all docs.")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
