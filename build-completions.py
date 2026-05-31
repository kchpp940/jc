#!/usr/bin/env python3
"""
Generate Bash and Zsh shell completion script content.

This module provides pure functions that return completion content as strings.
File writing is handled exclusively by generate_docs.py.

Usage (deprecated, for debugging only):
    python build-completions.py --stdout bash   # Print bash completion to stdout
    python build-completions.py --stdout zsh    # Print zsh completion to stdout

For normal use:
    python generate_docs.py             # Generate all docs consistently
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))


def generate_bash_completion_content() -> str:
    """Return Bash completion script content as a string. Does not write to disk."""
    from jc.shell_completions import bash_completion
    return bash_completion()


def generate_zsh_completion_content() -> str:
    """Return Zsh completion script content as a string. Does not write to disk."""
    from jc.shell_completions import zsh_completion
    return zsh_completion()


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
        print("  OLD: python build-completions.py", file=sys.stderr)
        print("  NEW: python generate_docs.py       (generates all docs)", file=sys.stderr)
        print(file=sys.stderr)
        print("For debugging (print content without writing files):", file=sys.stderr)
        print("  python build-completions.py --stdout bash", file=sys.stderr)
        print("  python build-completions.py --stdout zsh", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        sys.exit(1)

    shell = [a for a in sys.argv[1:] if a != '--stdout']
    if not shell or shell[0] == 'bash':
        print(generate_bash_completion_content())
    elif shell[0] == 'zsh':
        print(generate_zsh_completion_content())
    else:
        print(f"ERROR: Unknown shell '{shell[0]}'. Use 'bash' or 'zsh'.", file=sys.stderr)
        sys.exit(1)
