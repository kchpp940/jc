"""JC - JSON Convert

* kellyjonbrazil@gmail.com

This package converts the output of many standard unix command line tools
and file-types to dictionaries and lists of dictionaries.

## Interactive Documentation

Using `jc` in your python programs:

    >>> help('jc')
    >>> help('jc.lib')
    >>> jc.get_help('parser_module_name')

Developing `jc` parsers:

    >>> help('jc.utils')
    >>> help('jc.streaming')
    >>> help('jc.parsers.universal')

## Online Documentation

### Latest

https://github.com/kellyjonbrazil/jc/tree/master/docs

### Specific Version

`https://github.com/kellyjonbrazil/jc/tree/v<full_version_number>/docs`

> Replace `<full_version_number>` - e.g. `1.18.0`:

Specific versions can also be selected by tag in the Github branch dropdown
menu.

## Usage Example

    >>> import subprocess
    >>> import jc
    >>>
    >>> cmd_output = subprocess.check_output(['dig', 'example.com'],
                                             text=True)
    >>> data = jc.parse('dig', cmd_output)
    >>> data
    [{'id': 64612, 'opcode': 'QUERY', 'status': 'NOERROR', ...}]

Alternatively, you can bypass the high-level API and call the parser
modules directly:

    >>> import subprocess
    >>> import jc
    >>>
    >>> jc_dig = jc.get_parser('dig')
    >>> cmd_output = subprocess.check_output(['dig', 'example.com'],
                                             text=True)
    >>> data = jc_dig.parse(cmd_output)
    >>> data
    [{'id': 64612, 'opcode': 'QUERY', 'status': 'NOERROR', ...}]

or

    >>> import subprocess
    >>> import jc.parsers.dig
    >>>
    >>> cmd_output = subprocess.check_output(['dig', 'example.com'],
                                             text=True)
    >>> data = jc.parsers.dig.parse(cmd_output)
    >>> data
    [{'id': 64612, 'opcode': 'QUERY', 'status': 'NOERROR', ...}]

## Available Functions

Use `help(jc.lib)` for details.

### parse

    parse(
        parser_module_name: str,
        data: str | bytes | Iterable
    ) -> dict | list[dict] | Iterable[dict]

High-level API to easily access the parser. This API will find both
built-in parsers and local plugin parsers.

### get_parser

    get_parser(
        parser_module_name: str
    ) -> ModuleType

Get a parser Module object so you can use it directly.

### parser_info

    parser_info(
        parser_module_name: str,
        documentation: bool = False
    ) -> dict

Get the metadata for a particular parser.

### all_parser_info

    all_parser_info(documentation: bool = False) -> list[dict]

Get the metadata for all parsers.

### get_help

    get_help(parser_module_name: str) -> None

Convenience function to display the help screen for a parser using
its module name.

### parser_mod_list

    parser_mod_list() -> list[str]

Get a list of all available parser module names to be used in
`parse()`, `parser_info()`, and `get_help()`.

### plugin_parser_mod_list

    plugin_parser_mod_list() -> list[str]

Get a list of plugin parser module names to be used in
`parse()`, `parser_info()`, and `get_help()`. This list is a subset of
`parser_mod_list()`.

### standard_parser_mod_list

    standard_parser_mod_list() -> list[str]

Get a list of standard parser module names to be used in
`parse()`, `parser_info()`, and `get_help()`. This list is a subset of
`parser_mod_list()` and does not contain any streaming parsers.

### streaming_parser_mod_list

    streaming_parser_mod_list() -> list[str]

Get a list of streaming parser module names to be used in
`parse()`, `parser_info()`, and `get_help()`. This list is a subset of
`parser_mod_list()`.

### filter_parsers

    filter_parsers(
        category: str | list[str] | None = None,
        platform: str | list[str] | None = None,
        streaming: bool | None = None,
        slurpable: bool | None = None,
        plugin: bool | None = None,
        name: str | None = None,
        show_hidden: bool = False,
        show_deprecated: bool = False
    ) -> list[dict]

Filter and return parser metadata based on various criteria.

This is the unified parser discovery and filtering entrypoint used by
CLI, Python API, and shell completion.

All filter criteria are ANDed together. For list fields (category,
platform), a parser matches if any of its values intersects with the
filter values.

Example:

    >>> import jc
    >>> # Find all Linux-compatible streaming parsers
    >>> streaming_linux = jc.filter_parsers(platform='linux', streaming=True)
    >>> # Find all slurpable command parsers
    >>> slurpable_cmd = jc.filter_parsers(category=['command'], slurpable=True)

### ParserFilter

    ParserFilter dataclass for advanced parser filtering.

Use this to create reusable filter criteria objects.

### ParserList

    ParserList dataclass for parser discovery results.

This is the unified parser discovery result object used by CLI,
Python API, and shell completions. It provides multiple output
formats and convenience methods.

Example:

    >>> import jc
    >>> plist = jc.ParserList.discover(category='command', streaming=True)
    >>> print(f'Found {len(plist)} parsers')
    >>> print(plist.to_json(pretty=True))  # JSON for scripting
    >>> print(plist.to_yaml())             # YAML for scripting
    >>> print(plist.to_text())             # Human-readable text

    >>> # Access various data views
    >>> plist.names()            # Module names
    >>> plist.arguments()        # CLI argument names
    >>> plist.magic_commands()   # Magic command names
    >>> plist.by_category()      # Grouped by category tags
"""
from .lib import (
    __version__ as __version__,
    parse as parse,
    get_parser as get_parser,
    parser_mod_list as parser_mod_list,
    plugin_parser_mod_list as plugin_parser_mod_list,
    standard_parser_mod_list as standard_parser_mod_list,
    streaming_parser_mod_list as streaming_parser_mod_list,
    slurpable_parser_mod_list as slurpable_parser_mod_list,
    parser_info as parser_info,
    all_parser_info as all_parser_info,
    filter_parsers as filter_parsers,
    ParserFilter as ParserFilter,
    ParserList as ParserList,
    get_help as get_help
)
