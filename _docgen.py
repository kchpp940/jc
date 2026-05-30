#!/usr/bin/env python3
"""Repository-side shared tools for jc documentation generation scripts.

Contains repo-specific functionality that depends on the source repo
layout — project paths, Jinja2 template environment, and file output
helpers.  Re-exports runtime-safe views from jc._docgen for convenience
so that outer scripts only need one import.

Do NOT import this from within the installed jc package.
"""

from pathlib import Path
from typing import List, Dict

from jinja2 import Environment, FileSystemLoader

from jc._docgen import (
    get_jc_info,
    get_parsers,
    get_parser_names,
    is_parser_module,
    is_universal_module,
    is_standard_parser_module,
    get_magic_commands,
    get_all_options,
    get_completion_parsers,
    get_completion_parser_descriptions,
    get_zsh_command_descriptions,
    get_option_descriptions,
    get_filtered_options,
    get_release_metadata,
    ABOUT_OPTIONS,
    ABOUT_MOD_OPTIONS,
    HELP_OPTIONS,
    SPECIAL_OPTIONS,
)

PROJECT_ROOT: Path = Path(__file__).resolve().parent
TEMPLATES_DIR: Path = PROJECT_ROOT / "templates"
COMPLETIONS_DIR: Path = PROJECT_ROOT / "completions"
DOCS_DIR: Path = PROJECT_ROOT / "docs"
MAN_DIR: Path = PROJECT_ROOT / "man"
PARSERS_DIR: Path = PROJECT_ROOT / "jc" / "parsers"


def get_project_root() -> Path:
    return PROJECT_ROOT


def get_jinja_env(templates_dir: Path = TEMPLATES_DIR) -> Environment:
    return Environment(loader=FileSystemLoader(str(templates_dir)))


def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


__all__ = [
    'PROJECT_ROOT',
    'TEMPLATES_DIR',
    'COMPLETIONS_DIR',
    'DOCS_DIR',
    'MAN_DIR',
    'PARSERS_DIR',
    'ABOUT_OPTIONS',
    'ABOUT_MOD_OPTIONS',
    'HELP_OPTIONS',
    'SPECIAL_OPTIONS',
    'get_project_root',
    'get_jinja_env',
    'write_output',
    'get_jc_info',
    'get_parsers',
    'get_parser_names',
    'is_parser_module',
    'is_universal_module',
    'is_standard_parser_module',
    'get_magic_commands',
    'get_all_options',
    'get_completion_parsers',
    'get_completion_parser_descriptions',
    'get_zsh_command_descriptions',
    'get_option_descriptions',
    'get_filtered_options',
    'get_release_metadata',
]
