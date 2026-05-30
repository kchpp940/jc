"""jc - JSON Convert metadata module

Centralized metadata assembly for parsers and jc itself.

Layering:
  lib.py   → raw parser loading + minimal field dict (no derived fields)
  metadata → derived fields, filtering, and complete parser view

All consumers should use this module instead of directly calling
lib._raw_parser_info() or lib._raw_all_parser_info().
"""

import sys
from typing import List, Dict
from .jc_types import ParserInfoType, JSONDictType
from .lib import (
    jc_info, parsers, get_parser,
    _parser_is_streaming, _parser_is_hidden, _parser_is_deprecated,
    _parser_is_slurpable,
    parser_mod_list, standard_parser_mod_list, streaming_parser_mod_list,
    plugin_parser_mod_list, slurpable_parser_mod_list,
    _raw_parser_info,
    _raw_all_parser_info
)

__all__ = [
    'parser_info', 'all_parser_info',
    'jc_about', 'parser_doc_footer', 'parser_categories', 'magic_commands_dict'
]


def _enrich_parser_info(raw: ParserInfoType) -> ParserInfoType:
    """
    Compute derived fields on top of the raw info dict from lib._raw_parser_info().

    This is the single point where derived fields are assembled.
    """
    raw['compatibility_string'] = ', '.join(raw.get('compatible', ['unknown']))
    raw['is_slurpable'] = 'slurpable' in raw.get('tags', [])
    return raw


def parser_info(
    parser_mod_name,
    documentation: bool = False
) -> ParserInfoType:
    """
    Returns a dictionary that includes the parser module metadata
    with derived fields (compatibility_string, is_slurpable).

    This is the public API for getting parser metadata.
    """
    raw = _raw_parser_info(parser_mod_name, documentation=documentation)
    return _enrich_parser_info(raw)


def all_parser_info(
    documentation: bool = False,
    show_hidden: bool = False,
    show_deprecated: bool = False
) -> List[ParserInfoType]:
    """
    Returns a list of dictionaries that includes enriched metadata for all
    parser modules, with filtering and derived fields applied.

    This is the public API for getting all parser metadata.
    """
    raw_list = _raw_all_parser_info(
        documentation=documentation,
        show_hidden=show_hidden,
        show_deprecated=show_deprecated
    )
    return [_enrich_parser_info(p) for p in raw_list]


def jc_about() -> JSONDictType:
    """
    Returns jc info and the contents of each parser.info as a dictionary.

    This is the centralized assembly point for jc-level metadata.
    """
    return {
        'name': 'jc',
        'version': jc_info.version,
        'description': jc_info.description,
        'author': jc_info.author,
        'author_email': jc_info.author_email,
        'website': jc_info.website,
        'copyright': jc_info.copyright,
        'license': jc_info.license,
        'python_version': '.'.join((str(sys.version_info.major), str(sys.version_info.minor), str(sys.version_info.micro))),
        'python_path': sys.executable,
        'parser_count': len(parser_mod_list(show_hidden=True, show_deprecated=True)),
        'standard_parser_count': len(standard_parser_mod_list(show_hidden=True, show_deprecated=True)),
        'streaming_parser_count': len(streaming_parser_mod_list(show_hidden=True, show_deprecated=True)),
        'plugin_parser_count': len(plugin_parser_mod_list(show_hidden=True, show_deprecated=True)),
        'slurpable_parser_count': len(slurpable_parser_mod_list(show_hidden=True, show_deprecated=True)),
        'parsers': all_parser_info(show_hidden=True, show_deprecated=True)
    }


def parser_doc_footer(meta: ParserInfoType) -> str:
    """
    Returns the formatted documentation footer string for a parser.

    Expects a fully enriched info dict (with compatibility_string and
    is_slurpable already computed by _enrich_parser_info).
    """
    compatible = meta.get('compatibility_string', 'unknown')
    version = meta.get('version', 'unknown')
    author = meta.get('author', 'unknown')
    author_email = meta.get('author_email', 'unknown')

    slurpy = ''
    if meta.get('is_slurpable'):
        slurpy = 'This parser can be used with the `--slurp` command-line option.\n\n'

    return (
        f'Compatibility:  {compatible}\n\n'
        f'{slurpy}'
        f'Version {version} by {author} ({author_email})\n'
    )


def parser_categories(
    show_hidden: bool = True,
    show_deprecated: bool = False
) -> Dict[str, List[Dict[str, str]]]:
    """
    Returns parsers categorized by their tags.

    Each category maps to a list of dicts with 'arg' and 'desc' keys.
    """
    all_parsers = all_parser_info(show_hidden=show_hidden, show_deprecated=show_deprecated)

    generic = [{'arg': x['argument'], 'desc': x['description']} for x in all_parsers if 'generic' in x.get('tags', [])]
    standard = [{'arg': x['argument'], 'desc': x['description']} for x in all_parsers if 'standard' in x.get('tags', [])]
    command = [{'arg': x['argument'], 'desc': x['description']} for x in all_parsers if 'command' in x.get('tags', [])]
    slurpable = [{'arg': x['argument'], 'desc': x['description']} for x in all_parsers if x.get('is_slurpable')]
    file_str_bin = [
        {'arg': x['argument'], 'desc': x['description']} for x in all_parsers
        if 'file' in x.get('tags', []) or 'string' in x.get('tags', []) or 'binary' in x.get('tags', [])
    ]
    streaming = [{'arg': x['argument'], 'desc': x['description']} for x in all_parsers if x.get('streaming')]

    return {
        'Generic Parsers:': generic,
        'Standard Spec Parsers:': standard,
        'File/String/Binary Parsers:': file_str_bin,
        'Slurpable Parsers:': slurpable,
        'Streaming Parsers:': streaming,
        'Command Parsers:': command
    }


def magic_commands_dict() -> Dict[str, str]:
    """
    Returns a dictionary mapping magic command names to parser arguments.

    Used for magic syntax parsing (e.g. `jc -p ls -al`).
    """
    magic_dict: Dict[str, str] = {}
    for entry in all_parser_info():
        magic_dict.update({mc: entry['argument'] for mc in entry.get('magic_commands', [])})
    return magic_dict
