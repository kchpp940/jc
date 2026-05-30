#!/usr/bin/env python3
"""
Documentation Integrity Check for JC Parsers

Validates that parsers have complete enhanced documentation metadata:
- example_input: Example input text
- example_output: Dict with 'processed' and 'raw' keys
- platform_limitations: List of platform caveats
- common_exceptions: List of common exceptions with name and description

Usage:
    python3 doccheck.py              # Show full summary for all parsers
    python3 doccheck.py --verbose    # Show detailed missing fields
    python3 doccheck.py --strict     # Exit with error only if new/changed parsers are incomplete
    python3 doccheck.py --new        # Only check new/changed parsers (git diff)
    python3 doccheck.py <parser>     # Check specific parser
"""
import sys
import argparse
from typing import List, Dict, Tuple
import jc.lib
from jc.docrules import check_parser, is_doc_complete, get_changed_parsers


def get_all_parsers() -> List[str]:
    return [p['name'] for p in jc.lib.all_parser_info(show_hidden=False, show_deprecated=False)]


def generate_report(
    verbose: bool = False,
    only_changed: bool = False
) -> Tuple[List[str], int, int, List[str]]:
    all_parsers = get_all_parsers()
    changed_parsers = get_changed_parsers()
    complete_count = 0
    incomplete_changed = []
    report = []

    if only_changed and changed_parsers:
        parsers_to_check = sorted(p for p in changed_parsers if p in all_parsers)
        report.append('JC Parser Documentation Integrity Check (new/changed parsers)')
    else:
        parsers_to_check = sorted(all_parsers)
        report.append('JC Parser Documentation Integrity Check')

    report.append('=' * 50)
    report.append('')

    for parser_name in parsers_to_check:
        info = jc.lib.parser_info(parser_name)
        missing = check_parser(info)
        is_changed = parser_name in changed_parsers

        if not missing:
            status = '✓ COMPLETE'
            complete_count += 1
            if verbose:
                report.append(f'{parser_name:30} {status}')
        else:
            if is_changed:
                status = '✗ INCOMPLETE (new/changed)'
                incomplete_changed.append(parser_name)
            else:
                status = '✗ INCOMPLETE'
            report.append(f'{parser_name:30} {status}')
            if verbose:
                for m in missing:
                    report.append(f'    - {m}')
                report.append('')

    if not verbose:
        report.append('')
        report.append('Use --verbose to see details on incomplete parsers.')

    report.append('')
    report.append('=' * 50)
    report.append(f'Summary: {complete_count}/{len(parsers_to_check)} parsers checked have complete documentation')
    report.append(f'         {len(parsers_to_check) - complete_count} parsers need enhanced documentation')

    if incomplete_changed:
        report.append('')
        report.append('⚠ New/changed parsers missing documentation (blocks --strict):')
        for p in incomplete_changed:
            report.append(f'  - {p}')
    elif changed_parsers:
        report.append('')
        report.append('✓ All new/changed parsers have complete documentation.')

    return report, complete_count, len(parsers_to_check), incomplete_changed


def main() -> int:
    parser = argparse.ArgumentParser(description='Check JC parser documentation integrity')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed missing fields')
    parser.add_argument('--strict', '-s', action='store_true',
                        help='Exit with error only if new/changed parsers are incomplete')
    parser.add_argument('--new', '-n', action='store_true',
                        help='Only check new/changed parsers (git diff)')
    parser.add_argument('parser_name', nargs='?', help='Check a specific parser')

    args = parser.parse_args()

    if args.parser_name:
        missing, info = check_parser_with_info(args.parser_name)
        if not info:
            print(f'Error: Could not find parser "{args.parser_name}"')
            return 1

        print(f'Parser: {args.parser_name}')
        print(f'Description: {info.get("description", "N/A")}')
        print(f'Compatible: {", ".join(info.get("compatible", []))}')
        print()

        if missing:
            print('Missing/Incomplete fields:')
            for m in missing:
                print(f'  ✗ {m}')
            print()
            print(f'Status: INCOMPLETE ({len(missing)} issues)')
            return 2 if args.strict else 0
        else:
            print('Status: ✓ COMPLETE')
            return 0

    report, complete, total, incomplete_changed = generate_report(
        verbose=args.verbose,
        only_changed=args.new
    )
    print('\n'.join(report))

    if args.strict and incomplete_changed:
        return 1

    return 0


def check_parser_with_info(parser_name: str) -> Tuple[List[str], Dict]:
    try:
        info = jc.lib.parser_info(parser_name)
    except Exception as e:
        return [f'ERROR: Could not load parser: {e}'], {}

    missing = check_parser(info)
    return missing, info


if __name__ == '__main__':
    sys.exit(main())
