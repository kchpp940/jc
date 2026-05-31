#!/usr/bin/env python3
"""
Unified documentation generation script for jc.

Generates all documentation in the correct order to guarantee consistency.
Only this script is allowed to write documentation files to disk.

Order:
  1. Parser markdown docs  (from docstrings via doc2md.generate_module_doc)
  2. README.md             (from metadata  via readmegen.generate_readme_content)
  3. Man page              (from metadata  via mangen.generate_man_page_content)
  4. Shell completions     (from metadata  via build-completions.generate_*_content)

Usage:
    python generate_docs.py             # Full generation (always all parsers)
    python generate_docs.py --check     # Dry-run: verify nothing would change
    python generate_docs.py --diff      # Show diff of what would change
"""

import sys
import difflib
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).parent.absolute()
JC_DIR = PROJECT_ROOT / 'jc'
DOCS_DIR = PROJECT_ROOT / 'docs'
PARSERS_DOCS_DIR = DOCS_DIR / 'parsers'
COMPLETIONS_DIR = PROJECT_ROOT / 'completions'
MAN_DIR = PROJECT_ROOT / 'man'

sys.path.insert(0, str(PROJECT_ROOT))


class DocGenerationError(Exception):
    pass


def _write_if_changed(path: Path, content: str, label: str,
                      check_only: bool = False, show_diff: bool = False) -> bool:
    """
    Write *content* to *path* only if it differs from the current file.

    Returns True if the file was (or would be) written.
    In check-only mode, returns True when a mismatch is detected (treated as failure).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = ''
    if path.exists():
        existing = path.read_text(encoding='utf-8')

    if existing == content:
        print(f"  {label}: up-to-date")
        return True

    if check_only:
        if show_diff:
            diff = difflib.unified_diff(
                existing.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=str(path),
                tofile=str(path) + ' (generated)',
            )
            sys.stdout.writelines(diff)
        print(f"  {label}: STALE (would update)")
        return False

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  {label}: updated")
    return True


def _step(step_num: int, total: int, name: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"Step {step_num}/{total}: {name}")
    print(f"{'=' * 60}")


def generate_parser_docs(check_only: bool = False, show_diff: bool = False) -> bool:
    """Step 1 – generate all parser markdown docs (full, no incremental)."""
    from doc2md import generate_module_doc
    from jc.lib import all_parser_info

    print("Building parser markdown documentation (full)...")

    core_modules: List[Tuple[str, Path]] = [
        ('jc', DOCS_DIR / 'readme.md'),
        ('jc.lib', DOCS_DIR / 'lib.md'),
        ('jc.utils', DOCS_DIR / 'utils.md'),
        ('jc.streaming', DOCS_DIR / 'streaming.md'),
        ('jc.parsers.universal', PARSERS_DOCS_DIR / 'universal.md'),
    ]

    ok = True
    for mod_path, out_path in core_modules:
        try:
            content = generate_module_doc(mod_path)
            label = mod_path.replace('jc.parsers.', '').replace('jc.', '')
            if not _write_if_changed(out_path, content, label, check_only, show_diff):
                ok = False
        except Exception as e:
            print(f"  {mod_path}: FAILED ({e})")
            ok = False

    parser_infos = [
        p for p in all_parser_info(show_hidden=True, show_deprecated=True)
        if not p.get('plugin')
    ]

    for pinfo in parser_infos:
        name = pinfo['name']
        if name == 'universal':
            continue
        parser_file = JC_DIR / 'parsers' / f'{name}.py'
        if not parser_file.exists():
            continue
        try:
            content = generate_module_doc(f'jc.parsers.{name}')
            if not _write_if_changed(PARSERS_DOCS_DIR / f'{name}.md', content, name, check_only, show_diff):
                ok = False
        except Exception as e:
            print(f"  {name}: FAILED ({e})")
            ok = False

    if ok:
        print("++++ Parser markdown docs complete")
    else:
        print("---- Parser markdown docs had issues")
    return ok


def generate_readme(check_only: bool = False, show_diff: bool = False) -> bool:
    """Step 2 – generate README.md."""
    from readmegen import generate_readme_content

    print("Building README.md...")
    try:
        content = generate_readme_content()
        ok = _write_if_changed(PROJECT_ROOT / 'README.md', content, 'README.md', check_only, show_diff)
        if ok and not check_only:
            print("++++ README.md complete")
        elif not ok and check_only:
            print("---- README.md is stale")
        return ok
    except Exception as e:
        print(f"---- README.md FAILED ({e})")
        return False


def generate_man_page(check_only: bool = False, show_diff: bool = False) -> bool:
    """Step 3 – generate man page."""
    from mangen import generate_man_page_content

    print("Building man page...")
    try:
        content = generate_man_page_content()
        ok = _write_if_changed(MAN_DIR / 'jc.1', content, 'man/jc.1', check_only, show_diff)
        if ok and not check_only:
            print("++++ Man page complete")
        elif not ok and check_only:
            print("---- man/jc.1 is stale")
        return ok
    except Exception as e:
        print(f"---- Man page FAILED ({e})")
        return False


def generate_completions(check_only: bool = False, show_diff: bool = False) -> bool:
    """Step 4 – generate shell completion scripts."""
    import importlib
    _build_completions = importlib.import_module('build-completions')
    generate_bash_completion_content = _build_completions.generate_bash_completion_content
    generate_zsh_completion_content = _build_completions.generate_zsh_completion_content

    print("Building shell completion scripts...")
    ok = True
    try:
        bash_content = generate_bash_completion_content()
        if not _write_if_changed(COMPLETIONS_DIR / 'jc_bash_completion.sh', bash_content,
                                 'completions/jc_bash_completion.sh', check_only, show_diff):
            ok = False
    except Exception as e:
        print(f"---- Bash completion FAILED ({e})")
        ok = False

    try:
        zsh_content = generate_zsh_completion_content()
        if not _write_if_changed(COMPLETIONS_DIR / 'jc_zsh_completion.sh', zsh_content,
                                 'completions/jc_zsh_completion.sh', check_only, show_diff):
            ok = False
    except Exception as e:
        print(f"---- Zsh completion FAILED ({e})")
        ok = False

    if ok and not check_only:
        print("++++ Shell completions complete")
    elif not ok and check_only:
        print("---- Shell completions are stale")
    return ok


def generate_all_docs(check_only: bool = False, show_diff: bool = False) -> bool:
    """Run all four steps in order. Returns True only if every step succeeds."""
    start = datetime.now()
    mode = "CHECK" if check_only else "GENERATION"
    print(f"Documentation {mode} started at {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Project root: {PROJECT_ROOT}")

    steps = [
        ("Parser Markdown Docs", generate_parser_docs),
        ("README.md", generate_readme),
        ("Man Page", generate_man_page),
        ("Shell Completions", generate_completions),
    ]

    all_ok = True
    for i, (name, func) in enumerate(steps, 1):
        _step(i, len(steps), name)
        if not func(check_only=check_only, show_diff=show_diff):
            all_ok = False

    elapsed = (datetime.now() - start).total_seconds()
    print(f"\n{'=' * 60}")
    if all_ok:
        if check_only:
            print(f"++++ All documentation is up-to-date ({elapsed:.1f}s)")
        else:
            print(f"++++ All documentation generated successfully ({elapsed:.1f}s)")
    else:
        if check_only:
            print(f"---- Documentation drift detected ({elapsed:.1f}s)")
        else:
            print(f"---- Documentation generation had failures ({elapsed:.1f}s)")
    print(f"{'=' * 60}\n")
    return all_ok


def main() -> int:
    args = set(sys.argv[1:])
    check_only = '--check' in args
    show_diff = '--diff' in args

    if show_diff:
        check_only = True

    ok = generate_all_docs(check_only=check_only, show_diff=show_diff)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
