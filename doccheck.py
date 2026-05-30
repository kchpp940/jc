#!/usr/bin/env python3
"""Check jc documentation and metadata integrity."""

import sys
from pathlib import Path

from _docgen import (
    get_parsers,
    get_parser_names,
    get_release_metadata,
    is_standard_parser_module,
    DOCS_DIR,
    MAN_DIR,
    COMPLETIONS_DIR,
    PROJECT_ROOT,
    PARSERS_DIR,
)


def check_required_files() -> list:
    """Check that all required generated files exist."""
    errors = []
    required_files = [
        PROJECT_ROOT / 'README.md',
        MAN_DIR / 'jc.1',
        COMPLETIONS_DIR / 'jc_bash_completion.sh',
        COMPLETIONS_DIR / 'jc_zsh_completion.sh',
        DOCS_DIR / 'readme.md',
        DOCS_DIR / 'lib.md',
        DOCS_DIR / 'utils.md',
        DOCS_DIR / 'streaming.md',
    ]
    for f in required_files:
        if not f.exists():
            errors.append(f'Missing required file: {f}')
    return errors


def check_parser_docs() -> list:
    """Check that every non-hidden standard parser has a .md doc file."""
    errors = []
    parser_docs_dir = DOCS_DIR / 'parsers'
    parser_names = get_parser_names(show_hidden=False, show_deprecated=True)

    for name in parser_names:
        mod_path = f'jc.parsers.{name}'
        if not is_standard_parser_module(mod_path):
            continue

        doc_path = parser_docs_dir / f'{name}.md'
        if not doc_path.exists():
            errors.append(f'Missing doc for parser {name}: {doc_path}')

    return errors


def check_parser_info_fields() -> list:
    """Check that every parser has required info fields."""
    errors = []
    required_fields = [
        'name', 'argument', 'description', 'version',
        'author', 'author_email', 'compatible',
    ]
    parsers = get_parsers(show_hidden=True, show_deprecated=True)

    for p in parsers:
        for field in required_fields:
            if field not in p:
                errors.append(
                    f"Parser {p.get('name', 'UNKNOWN')} missing info field: {field}"
                )
    return errors


def check_release_metadata() -> list:
    """Check that release metadata has all required fields."""
    errors = []
    meta = get_release_metadata()
    required_fields = [
        'name', 'version', 'description', 'author',
        'author_email', 'website', 'copyright', 'license',
    ]
    for field in required_fields:
        if field not in meta or not meta[field]:
            errors.append(f'Release metadata missing or empty field: {field}')

    if meta.get('version') == 'unknown':
        errors.append('Release metadata version is "unknown"')

    return errors


def check_parser_modules() -> list:
    """Check that every parser listed in lib.py has a corresponding .py file."""
    errors = []
    parser_names = get_parser_names(show_hidden=True, show_deprecated=True)

    for name in parser_names:
        # Special parsers that don't have their own files
        if name in ('disabled_parser', 'broken_parser'):
            continue
        py_path = PARSERS_DIR / f'{name}.py'
        if not py_path.exists():
            errors.append(f'Parser module file missing: {py_path}')

    return errors


def main() -> int:
    print('Running jc documentation integrity checks...')
    print()

    all_errors = []

    checks = [
        ('Required generated files', check_required_files),
        ('Parser .md documentation files', check_parser_docs),
        ('Parser info fields', check_parser_info_fields),
        ('Release metadata', check_release_metadata),
        ('Parser module files', check_parser_modules),
    ]

    for check_name, check_fn in checks:
        print(f'  Checking {check_name}...', end=' ')
        errors = check_fn()
        if errors:
            print('FAILED')
            for e in errors:
                print(f'    - {e}')
            all_errors.extend(errors)
        else:
            print('PASSED')

    print()
    if all_errors:
        print(f'{len(all_errors)} error(s) found.')
        return 1

    print('All checks passed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
