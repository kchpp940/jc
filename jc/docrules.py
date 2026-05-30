"""
Centralized documentation integrity rules for JC parsers.

All documentation completeness checks MUST go through this module to ensure
consistency across README, man page, jc --about, and doccheck --strict.
"""
from typing import List, Dict, Tuple, Set
import os
import subprocess


REQUIRED_FIELDS: List[Tuple[str, type, str]] = [
    ('example_input', str, 'Example input text'),
    ('example_output', dict, 'Example output dict (processed/raw)'),
    ('platform_limitations', list, 'Platform limitations list'),
    ('common_exceptions', list, 'Common exceptions list'),
]


def is_doc_complete(parser_info: Dict) -> bool:
    """Check if a parser has complete enhanced documentation.

    Returns True only if ALL four fields are present and valid:
    - example_input: non-empty string
    - example_output: dict with 'processed' and 'raw' keys
    - platform_limitations: non-empty list
    - common_exceptions: non-empty list where each item is a dict
                          with 'name' and 'description' keys
    """
    for field, expected_type, _ in REQUIRED_FIELDS:
        value = parser_info.get(field)

        if value is None:
            return False

        if not isinstance(value, expected_type):
            return False

        if isinstance(value, (str, list, dict)) and not value:
            return False

        if field == 'example_output':
            if 'processed' not in value or 'raw' not in value:
                return False

        if field == 'common_exceptions':
            for exc in value:
                if not isinstance(exc, dict):
                    return False
                if 'name' not in exc or 'description' not in exc:
                    return False

    return True


def check_parser(parser_info: Dict) -> List[str]:
    """Return a list of missing/incomplete field descriptions.

    Returns an empty list if all documentation is complete.
    """
    missing = []

    for field, expected_type, _ in REQUIRED_FIELDS:
        value = parser_info.get(field)

        if value is None:
            missing.append(f'{field} (missing)')
            continue

        if not isinstance(value, expected_type):
            missing.append(f'{field} (wrong type: expected {expected_type.__name__}, got {type(value).__name__})')
            continue

        if isinstance(value, (str, list, dict)) and not value:
            missing.append(f'{field} (empty)')
            continue

        if field == 'example_output':
            if 'processed' not in value:
                missing.append(f'{field} (missing "processed" key)')
            if 'raw' not in value:
                missing.append(f'{field} (missing "raw" key)')

        if field == 'common_exceptions':
            for i, exc in enumerate(value):
                if not isinstance(exc, dict):
                    missing.append(f'{field}[{i}] (not a dict)')
                    continue
                if 'name' not in exc:
                    missing.append(f'{field}[{i}] (missing "name" key)')
                if 'description' not in exc:
                    missing.append(f'{field}[{i}] (missing "description" key)')

    return missing


def get_changed_parsers(project_root: str = None) -> Set[str]:
    """Return set of parser names that are new or changed in git.

    Detects:
    - Files changed in HEAD~1
    - Files in the git staging area
    - Untracked (new) parser files

    Excludes template parsers ('foo', 'foo-s').
    """
    changed = set()
    if project_root is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    try:
        result = subprocess.run(
            ['git', 'diff', '--name-only', '--diff-filter=AM', 'HEAD~1'],
            capture_output=True, text=True, cwd=project_root
        )
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                parts = line.split('/')
                if len(parts) >= 3 and parts[0] == 'jc' and parts[1] == 'parsers' and parts[-1].endswith('.py'):
                    parser_name = parts[-1][:-3].replace('_', '-')
                    if parser_name not in ('foo', 'foo-s'):
                        changed.add(parser_name)

        result_staged = subprocess.run(
            ['git', 'diff', '--name-only', '--diff-filter=AM', '--cached'],
            capture_output=True, text=True, cwd=project_root
        )
        if result_staged.returncode == 0:
            for line in result_staged.stdout.strip().splitlines():
                parts = line.split('/')
                if len(parts) >= 3 and parts[0] == 'jc' and parts[1] == 'parsers' and parts[-1].endswith('.py'):
                    parser_name = parts[-1][:-3].replace('_', '-')
                    if parser_name not in ('foo', 'foo-s'):
                        changed.add(parser_name)

        result_untracked = subprocess.run(
            ['git', 'ls-files', '--others', '--exclude-standard', 'jc/parsers/'],
            capture_output=True, text=True, cwd=project_root
        )
        if result_untracked.returncode == 0:
            for line in result_untracked.stdout.strip().splitlines():
                parts = line.split('/')
                if len(parts) >= 2 and parts[-1].endswith('.py'):
                    parser_name = parts[-1][:-3].replace('_', '-')
                    if parser_name not in ('foo', 'foo-s'):
                        changed.add(parser_name)

    except Exception:
        pass

    return changed
