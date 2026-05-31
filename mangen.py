#!/usr/bin/env python3
"""
Generate man page content from jc metadata using jinja2 templates.

This module provides a pure function that returns man page content as a string.
File writing is handled exclusively by generate_docs.py.

Usage (deprecated, for debugging only):
    python mangen.py --stdout       # Print man page content to stdout

For normal use:
    python generate_docs.py             # Generate all docs consistently
"""
import sys
from pathlib import Path
from datetime import date

PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))


def generate_man_page_content() -> str:
    """Return man page content as a string. Does not write to disk."""
    import jc.cli
    from jinja2 import Environment, FileSystemLoader

    file_loader = FileSystemLoader(str(PROJECT_ROOT / 'templates'))
    env = Environment(loader=file_loader)
    template = env.get_template('manpage_template')
    return template.render(
        today=date.today(),
        jc=jc.cli.JcCli.about_jc()
    )


if __name__ == '__main__':
    if '--stdout' not in sys.argv:
        print("=" * 70, file=sys.stderr)
        print("ERROR: This script no longer writes files directly.", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print(file=sys.stderr)
        print("This script has been deprecated in favor of the unified", file=sys.stderr)
        print("documentation generator, which guarantees consistency between", file=sys.stderr)
        print("parser docs, README, man page, and shell completions.", file=sys.stderr)
        print(file=sys.stderr)
        print("Migration guide:", file=sys.stderr)
        print("  OLD: python mangen.py", file=sys.stderr)
        print("  NEW: python generate_docs.py       (generates all docs)", file=sys.stderr)
        print(file=sys.stderr)
        print("For debugging (print content without writing files):", file=sys.stderr)
        print("  python mangen.py --stdout", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        sys.exit(1)

    print(generate_man_page_content())
