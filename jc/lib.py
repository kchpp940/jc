"""jc - JSON Convert lib module"""
from __future__ import annotations

import sys
import os
import re
import importlib
from typing import List, Iterable, Optional, Union, Iterator, NamedTuple, Dict, TYPE_CHECKING
from types import ModuleType
from .jc_types import ParserInfoType, JSONDictType
from jc import appdirs
from jc import utils

if TYPE_CHECKING:
    from typing_extensions import TypeAlias


__version__ = '1.25.6'

# Original static parser list (parsers can also be added via plugins later)
_BUILTIN_PARSERS: List[str] = [
    'acpi',
    'airport',
    'airport-s',
    'amixer',
    'apt-cache-show',
    'apt-get-sqq',
    'arp',
    'asciitable',
    'asciitable-m',
    'blkid',
    'bluetoothctl',
    'cbt',
    'cef',
    'cef-s',
    'certbot',
    'chage',
    'cksum',
    'clf',
    'clf-s',
    'crontab',
    'crontab-u',
    'csv',
    'csv-s',
    'curl-head',
    'date',
    'datetime-iso',
    'debconf-show',
    'df',
    'dig',
    'dir',
    'dmidecode',
    'dpkg-l',
    'du',
    'efibootmgr',
    'email-address',
    'env',
    'ethtool',
    'file',
    'find',
    'findmnt',
    'finger',
    'free',
    'fstab',
    'git-log',
    'git-log-s',
    'git-ls-remote',
    'gpg',
    'group',
    'gshadow',
    'hash',
    'hashsum',
    'hciconfig',
    'history',
    'host',
    'hosts',
    'http-headers',
    'id',
    'ifconfig',
    'ini',
    'ini-dup',
    'iostat',
    'iostat-s',
    'ip-address',
    'ipconfig',
    'iptables',
    'ip-route',
    'iw-scan',
    'iwconfig',
    'jar-manifest',
    'jobs',
    'jwt',
    'kv',
    'kv-dup',
    'last',
    'ls',
    'ls-s',
    'lsattr',
    'lsb-release',
    'lsblk',
    'lsmod',
    'lsof',
    'lspci',
    'lsusb',
    'm3u',
    'mdadm',
    'mount',
    'mpstat',
    'mpstat-s',
    'needrestart',
    'netstat',
    'net-localgroup',
    'net-user',
    'nmcli',
    'nsd-control',
    'ntpq',
    'openvpn',
    'os-prober',
    'os-release',
    'pacman',
    'passwd',
    'path',
    'path-list',
    'pci-ids',
    'pgpass',
    'pidstat',
    'pidstat-s',
    'ping',
    'ping-s',
    'pip-list',
    'pip-show',
    'pkg-index-apk',
    'pkg-index-deb',
    'plist',
    'postconf',
    'proc',
    'proc-buddyinfo',
    'proc-cmdline',
    'proc-consoles',
    'proc-cpuinfo',
    'proc-crypto',
    'proc-devices',
    'proc-diskstats',
    'proc-filesystems',
    'proc-interrupts',
    'proc-iomem',
    'proc-ioports',
    'proc-loadavg',
    'proc-locks',
    'proc-meminfo',
    'proc-modules',
    'proc-mtrr',
    'proc-pagetypeinfo',
    'proc-partitions',
    'proc-slabinfo',
    'proc-softirqs',
    'proc-stat',
    'proc-swaps',
    'proc-uptime',
    'proc-version',
    'proc-vmallocinfo',
    'proc-vmstat',
    'proc-zoneinfo',
    'proc-driver-rtc',
    'proc-net-arp',
    'proc-net-dev',
    'proc-net-dev-mcast',
    'proc-net-if-inet6',
    'proc-net-igmp',
    'proc-net-igmp6',
    'proc-net-ipv6-route',
    'proc-net-netlink',
    'proc-net-netstat',
    'proc-net-packet',
    'proc-net-protocols',
    'proc-net-route',
    'proc-net-tcp',
    'proc-net-unix',
    'proc-pid-fdinfo',
    'proc-pid-io',
    'proc-pid-maps',
    'proc-pid-mountinfo',
    'proc-pid-numa-maps',
    'proc-pid-smaps',
    'proc-pid-stat',
    'proc-pid-statm',
    'proc-pid-status',
    'ps',
    'resolve-conf',
    'route',
    'route-print',
    'rpm-qi',
    'rsync',
    'rsync-s',
    'semver',
    'sfdisk',
    'shadow',
    'srt',
    'ss',
    'ssh-conf',
    'sshd-conf',
    'stat',
    'stat-s',
    'swapon',
    'sysctl',
    'syslog',
    'syslog-s',
    'syslog-bsd',
    'syslog-bsd-s',
    'systemctl',
    'systemctl-lj',
    'systemctl-ls',
    'systemctl-luf',
    'systeminfo',
    'time',
    'timedatectl',
    'timestamp',
    'toml',
    'top',
    'top-s',
    'tracepath',
    'traceroute',
    'traceroute-s',
    'tune2fs',
    'udevadm',
    'ufw',
    'ufw-appinfo',
    'uname',
    'update-alt-gs',
    'update-alt-q',
    'upower',
    'uptime',
    'url',
    'ver',
    'veracrypt',
    'vmstat',
    'vmstat-s',
    'w',
    'wc',
    'wg-show',
    'who',
    'x509-cert',
    'x509-crl',
    'x509-csr',
    'xml',
    'xrandr',
    'yaml',
    'zipinfo',
    'zpool-iostat',
    'zpool-status'
]

parsers: List[str] = list(_BUILTIN_PARSERS)

def _cliname_to_modname(parser_cli_name: str) -> str:
    return parser_cli_name.replace('--', '').replace('-', '_')

def _modname_to_cliname(parser_mod_name: str) -> str:
    return parser_mod_name.replace('_', '-')

def _is_valid_parser_plugin(name: str, local_parsers_dir: str) -> bool:
    if re.match(r'\w+\.py$', name) and os.path.isfile(os.path.join(local_parsers_dir, name)):
        try:
            parser_mod_name = _cliname_to_modname(name)[0:-3]
            modpath = 'jcparsers.'
            plugin =  importlib.import_module(f'{modpath}{parser_mod_name}')
            if hasattr(plugin, 'info') and hasattr(plugin, 'parse'):
                del plugin
                return True
            else:
                utils.warning_message([f'Not installing invalid parser plugin "{parser_mod_name}" at {local_parsers_dir}'])
                return False
        except Exception as e:
            utils.warning_message([f'Not installing parser plugin "{parser_mod_name}" at {local_parsers_dir} due to error: {e}'])
            return False
    return False

local_parsers: List[str] = []
data_dir = appdirs.user_data_dir('jc', 'jc')  # type: ignore
local_parsers_dir = os.path.join(data_dir, 'jcparsers')
if os.path.isdir(local_parsers_dir):
    sys.path.append(data_dir)
    for name in os.listdir(local_parsers_dir):
        if _is_valid_parser_plugin(name, local_parsers_dir):
            plugin_name = name[0:-3]
            local_parsers.append(_modname_to_cliname(plugin_name))
            if _modname_to_cliname(plugin_name) not in parsers:
                parsers.append(_modname_to_cliname(plugin_name))
    try:
        del name
    except Exception:
        pass


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
    """Return the parser module object using the unified index"""
    entry = _find_parser_entry(parser_mod_name)
    if entry is not None:
        return _load_parser_module(entry)
    
    mod_name = _cliname_to_modname(parser_mod_name)
    try:
        return importlib.import_module(f'jc.parsers.{mod_name}')
    except Exception as e:
        mod = importlib.import_module('jc.parsers.disabled_parser')
        mod.__name__ = mod_name
        utils.warning_message([f'"{mod_name}" parser disabled due to error: {e}'])
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


def _find_parser_entry(cli_or_mod_name: str) -> Optional[_ParserEntry]:
    """
    Find a parser entry in the index by CLI name or module name.
    Returns None if not found.
    """
    cli_name = _modname_to_cliname(_cliname_to_modname(cli_or_mod_name))
    for entry in _parser_index:
        if entry.cli_name == cli_name:
            return entry
    return None


def _load_parser_module(entry: _ParserEntry) -> ModuleType:
    """
    Load a parser module using the source from the index entry.
    This ensures plugin override priority is enforced.
    """
    modpath = 'jcparsers.' if entry.source == 'plugin' else 'jc.parsers.'
    try:
        return importlib.import_module(f'{modpath}{entry.mod_name}')
    except Exception as e:
        mod = importlib.import_module('jc.parsers.disabled_parser')
        mod.__name__ = entry.mod_name
        utils.warning_message([f'"{entry.mod_name}" parser disabled due to error: {e}'])
        return mod


class _ParserEntry(NamedTuple):
    cli_name: str
    mod_name: str
    argument: str
    source: str
    hidden: bool
    deprecated: bool
    streaming: bool
    slurpable: bool
    overrides_builtin: bool


def _build_parser_index() -> List[_ParserEntry]:
    index: List[_ParserEntry] = []
    for cli_name in parsers:
        mod_name = _cliname_to_modname(cli_name)
        is_plugin = cli_name in local_parsers
        source = 'plugin' if is_plugin else 'builtin'
        overrides_builtin = is_plugin and cli_name in _BUILTIN_PARSERS
        
        temp_entry = _ParserEntry(
            cli_name=cli_name,
            mod_name=mod_name,
            argument=f'--{cli_name}',
            source=source,
            hidden=False,
            deprecated=False,
            streaming=False,
            slurpable=False,
            overrides_builtin=overrides_builtin,
        )
        parser = _load_parser_module(temp_entry)
        hidden = bool(getattr(parser.info, 'hidden', None))
        deprecated = bool(getattr(parser.info, 'deprecated', None))
        streaming = bool(getattr(parser.info, 'streaming', None))
        tag_list = getattr(parser.info, 'tags', [])
        slurpable = 'slurpable' in tag_list
        
        index.append(_ParserEntry(
            cli_name=cli_name,
            mod_name=mod_name,
            argument=f'--{cli_name}',
            source=source,
            hidden=hidden,
            deprecated=deprecated,
            streaming=streaming,
            slurpable=slurpable,
            overrides_builtin=overrides_builtin,
        ))
    return index


_parser_index: List[_ParserEntry] = _build_parser_index()


def refresh_parser_index() -> List[_ParserEntry]:
    """
    Rescan the local plugins directory and rebuild the parser index.
    Useful when plugins are added or removed at runtime.

    Returns:
        The new parser index.
    """
    global _parser_index, parsers, local_parsers

    local_parsers.clear()
    parsers.clear()
    parsers.extend(_BUILTIN_PARSERS)

    if os.path.isdir(local_parsers_dir):
        for name in os.listdir(local_parsers_dir):
            if _is_valid_parser_plugin(name, local_parsers_dir):
                plugin_name = name[0:-3]
                plugin_cli_name = _modname_to_cliname(plugin_name)
                local_parsers.append(plugin_cli_name)
                if plugin_cli_name not in parsers:
                    parsers.append(plugin_cli_name)

    _parser_index = _build_parser_index()
    return _parser_index


def is_valid_parser(parser_name: str) -> bool:
    """
    Check if a parser name exists in the unified index.
    
    Parameters:
        parser_name: CLI name, module name, or --argument-name of the parser.
        
    Returns:
        True if the parser exists in the index, False otherwise.
    """
    return _find_parser_entry(parser_name) is not None


def parser_index(
    show_hidden: bool = False,
    show_deprecated: bool = False,
    source: Optional[str] = None,
    streaming_only: Optional[bool] = None,
    slurpable_only: bool = False,
    include_override_only: bool = False,
) -> List[Dict]:
    """
    Query the unified parser index with filtering options.

    All components (parser_info(), all_parser_info(), CLI -a, shell
    completions) should use this function to ensure a consistent view
    of available parsers.

    Parameters:

        show_hidden:            (bool)  include parsers marked as hidden
        show_deprecated:        (bool)  include parsers marked as deprecated
        source:                 (str)   filter by source: 'builtin' or 'plugin'
        streaming_only:         (bool)  if True, only streaming parsers;
                                        if False, only non-streaming parsers
        slurpable_only:         (bool)  only parsers supporting --slurp
        include_override_only:  (bool)  only plugins that override builtins

    Returns:

        List of dictionaries with keys:
            cli_name, mod_name, argument, source, hidden, deprecated,
            streaming, slurpable, overrides_builtin
    """
    result: List[Dict] = []
    for entry in _parser_index:
        if not show_hidden and entry.hidden:
            continue
        if not show_deprecated and entry.deprecated:
            continue
        if source is not None and entry.source != source:
            continue
        if streaming_only is True and not entry.streaming:
            continue
        if streaming_only is False and entry.streaming:
            continue
        if slurpable_only and not entry.slurpable:
            continue
        if include_override_only and not entry.overrides_builtin:
            continue
        result.append({
            'cli_name': entry.cli_name,
            'mod_name': entry.mod_name,
            'argument': entry.argument,
            'source': entry.source,
            'hidden': entry.hidden,
            'deprecated': entry.deprecated,
            'streaming': entry.streaming,
            'slurpable': entry.slurpable,
            'overrides_builtin': entry.overrides_builtin,
        })
    return result


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
    return [e['mod_name'] for e in parser_index(show_hidden=show_hidden, show_deprecated=show_deprecated)]

def plugin_parser_mod_list(
    show_hidden: bool = False,
    show_deprecated: bool = False
) -> List[str]:
    """
    Returns a list of plugin parser module names. This function is a
    subset of `parser_mod_list()`.
    """
    return [e['mod_name'] for e in parser_index(show_hidden=show_hidden, show_deprecated=show_deprecated, source='plugin')]

def standard_parser_mod_list(
    show_hidden: bool = False,
    show_deprecated: bool = False
) -> List[str]:
    """
    Returns a list of standard parser module names. This function is a
    subset of `parser_mod_list()` and does not contain any streaming
    parsers.
    """
    return [e['mod_name'] for e in parser_index(show_hidden=show_hidden, show_deprecated=show_deprecated, streaming_only=False)]

def streaming_parser_mod_list(
    show_hidden: bool = False,
    show_deprecated: bool = False
) -> List[str]:
    """
    Returns a list of streaming parser module names. This function is a
    subset of `parser_mod_list()`.
    """
    return [e['mod_name'] for e in parser_index(show_hidden=show_hidden, show_deprecated=show_deprecated, streaming_only=True)]

def slurpable_parser_mod_list(
    show_hidden: bool = False,
    show_deprecated: bool = False
) -> List[str]:
    """
    Returns a list of slurpable parser module names. This function is a
    subset of `parser_mod_list()`.
    """
    return [e['mod_name'] for e in parser_index(show_hidden=show_hidden, show_deprecated=show_deprecated, slurpable_only=True)]

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
    parser_cli_name = _modname_to_cliname(parser_mod_name)

    info_dict: ParserInfoType = {}
    info_dict['name'] = parser_mod_name
    info_dict['argument'] = f'--{parser_cli_name}'
    parser_entry = vars(parser_mod.info)

    for k, v in parser_entry.items():
        if not k.startswith('__'):
            info_dict[k] = v  # type: ignore

    is_plugin = parser_cli_name in local_parsers
    if is_plugin:
        info_dict['plugin'] = True
    info_dict['source'] = 'plugin' if is_plugin else 'builtin'
    info_dict['overrides_builtin'] = is_plugin and parser_cli_name in _BUILTIN_PARSERS

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
    filtered = parser_index(show_hidden=show_hidden, show_deprecated=show_deprecated)
    p_info_list: List[ParserInfoType] = [parser_info(e['cli_name'], documentation=documentation) for e in filtered]
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
