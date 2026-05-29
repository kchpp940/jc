"""jc - JSON Convert metadata policy module

This module defines standardized parser filtering policies for different use cases
(doc generation, README, man pages, shell completions, CLI, etc.).

All scripts should use these policy functions instead of directly calling
all_parser_info() with custom parameters, to ensure consistency across the project.
"""

from typing import List
from .lib import all_parser_info, ParserInfoType


def for_docs(documentation: bool = False) -> List[ParserInfoType]:
    """Parser filtering policy for parser documentation (docs/parsers/*.md).

    Includes:
    - Non-plugin parsers only
    - Hidden parsers (proc_*, etc.)
    - Excludes deprecated parsers

    Used by: docgen.sh
    """
    return [
        p for p in all_parser_info(
            documentation=documentation,
            show_hidden=True,
            show_deprecated=False
        )
        if not p.get('plugin', False)
    ]


def _visible_parsers(documentation: bool = False) -> List[ParserInfoType]:
    """Common policy for visible parsers (non-hidden, non-deprecated).

    Base policy shared by multiple use cases (CLI magic, shell completions,
    README, man page). Use the scenario-specific wrapper functions instead.
    """
    return all_parser_info(
        documentation=documentation,
        show_hidden=False,
        show_deprecated=False
    )


def for_readme() -> List[ParserInfoType]:
    """Parser filtering policy for README.md.

    Includes:
    - Non-hidden parsers only
    - Excludes deprecated parsers

    Used by: readmegen.py
    """
    return _visible_parsers()


def for_man_page() -> List[ParserInfoType]:
    """Parser filtering policy for man page.

    Includes:
    - Non-hidden parsers only
    - Excludes deprecated parsers

    Used by: mangen.py
    """
    return _visible_parsers()


def for_completion() -> List[ParserInfoType]:
    """Parser filtering policy for shell completion (both parser arguments
    and magic commands).

    Includes:
    - Non-hidden parsers only
    - Excludes deprecated parsers

    Used by: shell_completions.py (parser arguments and magic commands)
    """
    return _visible_parsers()


def for_cli_help(show_hidden: bool = False) -> List[ParserInfoType]:
    """Parser filtering policy for CLI --help output.

    Args:
        show_hidden: If True, include hidden parsers

    Used by: cli.py (help output)
    """
    return all_parser_info(
        documentation=False,
        show_hidden=show_hidden,
        show_deprecated=False
    )


def for_cli_about() -> List[ParserInfoType]:
    """Parser filtering policy for CLI --about output.

    Includes:
    - Hidden parsers
    - Deprecated parsers
    - (Plugin status is preserved in output)

    Used by: cli.py (jc -a output)
    """
    return all_parser_info(
        documentation=False,
        show_hidden=True,
        show_deprecated=True
    )


def for_cli_magic() -> List[ParserInfoType]:
    """Parser filtering policy for CLI magic syntax.

    Includes:
    - Non-hidden parsers only
    - Excludes deprecated parsers

    Used by: cli.py (magic command detection)
    """
    return _visible_parsers()
