"""jc - JSON Convert lib module"""
import importlib
from typing import List, Iterable, Optional, Union, Iterator
from types import ModuleType
from .jc_types import ParserInfoType, JSONDictType
from .registry import (
    registry, cliname_to_modname, modname_to_cliname,
)
from jc import utils


__version__ = '1.25.6'

parsers: List[str] = registry.parsers
local_parsers: List[str] = registry.plugin_parsers
disabled_parsers = registry.disabled_parsers
overridden_parsers = registry.overridden_parsers


def _cliname_to_modname(parser_cli_name: str) -> str:
    return cliname_to_modname(parser_cli_name)

def _modname_to_cliname(parser_mod_name: str) -> str:
    return modname_to_cliname(parser_mod_name)

def _parser_argument(parser_mod_name: str) -> str:
    parser = _modname_to_cliname(parser_mod_name)
    return f'--{parser}'

def get_parser(parser_mod_name: Union[str, ModuleType]) -> ModuleType:
    """
    Return the parser module object and check that the module is a valid
    parser module.

    Parameters:

        parser_mod_name:    (string or   Name of the parser module. This
                            Module)      function will accept module_name,
                                         cli-name, and --argument-name
                                         variants of the module name.

                                         If a Module is given and the Module
                                         is a valid parser Module, then the
                                         same Module is returned.

    Returns:

        Module:  the parser Module object

    Raises:

        ModuleNotFoundError:  If the Module is not found or is not a valid
                              parser Module, then a ModuleNotFoundError
                              exception is raised.
    """
    if isinstance(parser_mod_name, ModuleType):
        jc_parser = parser_mod_name
    else:
        try:
            jc_parser = _get_parser(parser_mod_name)
        except ModuleNotFoundError:
            raise ModuleNotFoundError(f'"{parser_mod_name}" is not found or is not a valid parser module.')

    if not hasattr(jc_parser, 'info') or not hasattr(jc_parser, 'parse'):
        raise ModuleNotFoundError(f'"{jc_parser}" is not a valid parser module.')

    return jc_parser

def _get_parser(parser_mod_name: str) -> ModuleType:
    """Return the parser module object"""
    parser_mod_name = _cliname_to_modname(parser_mod_name)
    parser_cli_name = _modname_to_cliname(parser_mod_name)

    cached = registry.get_cached_module(parser_cli_name)
    if cached is not None:
        return cached

    modpath: str = 'jcparsers.' if registry.is_plugin(parser_cli_name) else 'jc.parsers.'
    mod = None

    try:
        mod = importlib.import_module(f'{modpath}{parser_mod_name}')
        registry.cache_module(parser_cli_name, mod)
    except Exception as e:
        mod = importlib.import_module('jc.parsers.disabled_parser')
        mod.__name__ = parser_mod_name
        registry.mark_disabled(parser_cli_name)
        utils.warning_message([f'"{parser_mod_name}" parser disabled due to error: {e}'])

    return mod

def _parser_is_slurpable(parser: ModuleType) -> bool:
    tag_list = getattr(parser.info, 'tags', [])
    if 'slurpable' in tag_list:
        return True
    return False

def _parser_is_streaming(parser: ModuleType) -> bool:
    if getattr(parser.info, 'streaming', None):
        return True
    return False

def _parser_is_hidden(parser: ModuleType) -> bool:
    if getattr(parser.info, 'hidden', None):
        return True
    return False

def _parser_is_deprecated(parser: ModuleType) -> bool:
    if getattr(parser.info, 'deprecated', None):
        return True
    return False

def parse(
    parser_mod_name: Union[str, ModuleType],
    data: Union[str, bytes, Iterable[str]],
    quiet: bool = False,
    raw: bool = False,
    ignore_exceptions: Optional[bool] = None,
    **kwargs
) -> Union[JSONDictType, List[JSONDictType], Iterator[JSONDictType]]:
    """
    Parse the data (string or bytes) using the supplied parser (string or
    module object).

    This function provides a high-level API to simplify parser use. This
    function will call built-in parsers and custom plugin parsers.

    Example (standard parsers):

        >>> import jc
        >>> date_obj = jc.parse('date', 'Tue Jan 18 10:23:07 PST 2022')
        >>> print(f'The year is: {date_obj["year"]}')
        The year is: 2022

    Example (streaming parsers):

        >>> import jc
        >>> ping_gen = jc.parse('ping_s', ping_output.splitlines())
        >>> for item in ping_gen:
        >>>     print(f'Response time: {item["time_ms"]} ms')
        Response time: 102 ms
        Response time: 109 ms
        ...

    To get a list of available parser module names, use `parser_mod_list()`.

    Alternatively, a parser module object can be supplied:

        >>> import jc
        >>> jc_date = jc.get_parser('date')
        >>> date_obj = jc.parse(jc_date, 'Tue Jan 18 10:23:07 PST 2022')
        >>> print(f'The year is: {date_obj["year"]}')
        The year is: 2022

    You can also use the parser modules directly via `get_parser()`:

        >>> import jc
        >>> jc_date = jc.get_parser('date')
        >>> date_obj = jc_date.parse('Tue Jan 18 10:23:07 PST 2022')
        >>> print(f'The year is: {date_obj["year"]}')
        The year is: 2022

    Finally, you can access the low-level parser modules manually:

        >>> import jc.parsers.date
        >>> date_obj = jc.parsers.date.parse('Tue Jan 18 10:23:07 PST 2022')
        >>> print(f'The year is: {date_obj["year"]}')
        The year is: 2022

    Though, accessing plugin parsers directly is a bit more cumbersome, so
    this higher-level API is recommended. Here is how you can access plugin
    parsers without this API:

        >>> import os
        >>> import sys
        >>> import jc.appdirs
        >>> data_dir = jc.appdirs.user_data_dir('jc', 'jc')
        >>> local_parsers_dir = os.path.join(data_dir, 'jcparsers')
        >>> sys.path.append(local_parsers_dir)
        >>> import my_custom_parser
        >>> my_custom_parser.parse('command_data')

    Parameters:

        parser_mod_name:    (string or   name of the parser module. This
                            Module)      function will accept module_name,
                                         cli-name, and --argument-name
                                         variants of the module name.

                                         A Module object can also be passed
                                         directly or via `get_parser()`

        data:               (string or   data to parse (string or bytes for
                            bytes or     standard parsers, iterable of
                            iterable)    strings for streaming parsers)

        raw:                (boolean)    output preprocessed JSON if `True`

        quiet:              (boolean)    suppress warning messages if `True`

        ignore_exceptions:  (boolean)    ignore parsing exceptions if `True`
                                         (streaming parsers only)

    Returns:

        Standard Parsers:   Dictionary or List of Dictionaries
        Streaming Parsers:  Generator Object containing Dictionaries
    """
    jc_parser = get_parser(parser_mod_name)

    if ignore_exceptions is not None:
        return jc_parser.parse(
            data,
            quiet=quiet,
            raw=raw,
            ignore_exceptions=ignore_exceptions,
            **kwargs
        )

    return jc_parser.parse(data, quiet=quiet, raw=raw, **kwargs)

def parser_mod_list(
    show_hidden: bool = False,
    show_deprecated: bool = False
) -> List[str]:
    """Returns a list of all available parser module names."""
    plist: List[str] = []
    for p in parsers:
        parser = get_parser(p)

        if not show_hidden and _parser_is_hidden(parser):
            continue

        if not show_deprecated and _parser_is_deprecated(parser):
            continue

        plist.append(_cliname_to_modname(p))

    return plist

def plugin_parser_mod_list(
    show_hidden: bool = False,
    show_deprecated: bool = False
) -> List[str]:
    """
    Returns a list of plugin parser module names. This function is a
    subset of `parser_mod_list()`.
    """
    plist: List[str] = []
    for p in local_parsers:
        parser = get_parser(p)

        if not show_hidden and _parser_is_hidden(parser):
            continue

        if not show_deprecated and _parser_is_deprecated(parser):
            continue

        plist.append(_cliname_to_modname(p))

    return plist

def standard_parser_mod_list(
    show_hidden: bool = False,
    show_deprecated: bool = False
) -> List[str]:
    """
    Returns a list of standard parser module names. This function is a
    subset of `parser_mod_list()` and does not contain any streaming
    parsers.
    """
    plist: List[str] = []
    for p in parsers:
        parser = get_parser(p)

        if not _parser_is_streaming(parser):

            if not show_hidden and _parser_is_hidden(parser):
                continue

            if not show_deprecated and _parser_is_deprecated(parser):
                continue

            plist.append(_cliname_to_modname(p))

    return plist

def streaming_parser_mod_list(
    show_hidden: bool = False,
    show_deprecated: bool = False
) -> List[str]:
    """
    Returns a list of streaming parser module names. This function is a
    subset of `parser_mod_list()`.
    """
    plist: List[str] = []
    for p in parsers:
        parser = get_parser(p)

        if _parser_is_streaming(parser):

            if not show_hidden and _parser_is_hidden(parser):
                continue

            if not show_deprecated and _parser_is_deprecated(parser):
                continue

            plist.append(_cliname_to_modname(p))

    return plist

def slurpable_parser_mod_list(
    show_hidden: bool = False,
    show_deprecated: bool = False
) -> List[str]:
    """
    Returns a list of slurpable parser module names. This function is a
    subset of `parser_mod_list()`.
    """
    plist: List[str] = []
    for p in parsers:
        parser = get_parser(p)

        if _parser_is_slurpable(parser):

            if not show_hidden and _parser_is_hidden(parser):
                continue

            if not show_deprecated and _parser_is_deprecated(parser):
                continue

            plist.append(_cliname_to_modname(p))

    return plist

def parser_info(
    parser_mod_name: Union[str, ModuleType],
    documentation: bool = False
) -> ParserInfoType:
    """
    Returns a dictionary that includes the parser module metadata.

    Parameters:

        parser_mod_name:    (string or   name of the parser module. This
                            Module)      function will accept module_name,
                                         cli-name, and --argument-name
                                         variants of the module name as well
                                         as a parser module object.

        documentation:      (boolean)    include parser docstring if `True`
    """
    parser_mod = get_parser(parser_mod_name)
    parser_mod_name = parser_mod.__name__.split('.')[-1]

    info_dict: ParserInfoType = {}
    info_dict['name'] = parser_mod_name
    info_dict['argument'] = _parser_argument(parser_mod_name)
    parser_entry = vars(parser_mod.info)

    for k, v in parser_entry.items():
        if not k.startswith('__'):
            info_dict[k] = v  # type: ignore

    cliname = _modname_to_cliname(parser_mod_name)

    if registry.is_plugin(cliname):
        info_dict['plugin'] = True

    if registry.is_overridden(cliname):
        info_dict['overrides_builtin'] = True

    if registry.is_disabled(cliname):
        info_dict['disabled'] = True

    if registry.is_broken(cliname):
        info_dict['broken'] = True

    if documentation:
        docs = parser_mod.__doc__
        if not docs:
            docs = 'No documentation available.\n'
        info_dict['documentation'] = docs

    return info_dict

def all_parser_info(
    documentation: bool = False,
    show_hidden: bool = False,
    show_deprecated: bool = False
) -> List[ParserInfoType]:
    """
    Returns a list of dictionaries that includes metadata for all parser
    modules. By default only non-hidden, non-deprecated parsers are
    returned.

    Parameters:

        documentation:      (boolean)    include parser docstrings if `True`
        show_hidden:        (boolean)    also show parsers marked as hidden
                                         in their info metadata.
        show_deprecated:    (boolean)    also show parsers marked as
                                         deprecated in their info metadata.
    """
    plist: List[str] = []
    for p in parsers:
        parser = get_parser(p)

        if not show_hidden and _parser_is_hidden(parser):
            continue

        if not show_deprecated and _parser_is_deprecated(parser):
            continue

        plist.append(p)

    p_info_list: List[ParserInfoType] = [parser_info(p, documentation=documentation) for p in plist]

    return p_info_list

def get_help(parser_mod_name: Union[str, ModuleType]) -> None:
    """
    Show help screen for the selected parser.

    This function will accept **module_name**, **cli-name**, and
    **--argument-name** variants of the module name string as well as a
    parser module object.
    """
    jc_parser = get_parser(parser_mod_name)
    help(jc_parser)
