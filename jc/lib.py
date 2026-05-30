"""jc - JSON Convert lib module"""
import sys
import os
import re
import json
import importlib
from typing import List, Iterable, Optional, Union, Iterator, Dict
from types import ModuleType
from dataclasses import dataclass, field
from .jc_types import ParserInfoType, JSONDictType
from jc import appdirs
from jc import utils


@dataclass
class ParserFilter:
    """
    Filter criteria for parser discovery.

    All filter criteria are ANDed together. For list fields (category,
    platform), a parser matches if any of its values intersects with the
    filter values.
    """
    category: Optional[List[str]] = field(default=None)
    platform: Optional[List[str]] = field(default=None)
    streaming: Optional[bool] = field(default=None)
    slurpable: Optional[bool] = field(default=None)
    plugin: Optional[bool] = field(default=None)
    name: Optional[str] = field(default=None)

    def matches(self, parser_info: ParserInfoType) -> bool:
        """Check if a parser matches this filter."""
        if self.name is not None:
            if self.name not in parser_info.get('name', '') and \
               self.name not in parser_info.get('argument', ''):
                return False

        if self.category is not None:
            tags = parser_info.get('tags', [])
            if not any(cat in tags for cat in self.category):
                return False

        if self.platform is not None:
            compatible = parser_info.get('compatible', [])
            if not any(plat in compatible for plat in self.platform):
                return False

        if self.streaming is not None:
            if bool(parser_info.get('streaming', False)) != self.streaming:
                return False

        if self.slurpable is not None:
            tags = parser_info.get('tags', [])
            if ('slurpable' in tags) != self.slurpable:
                return False

        if self.plugin is not None:
            if bool(parser_info.get('plugin', False)) != self.plugin:
                return False

        return True

    def to_dict(self) -> Dict:
        """Serialize filter criteria to a dictionary."""
        result: Dict = {}
        if self.category is not None:
            result['category'] = self.category
        if self.platform is not None:
            result['platform'] = self.platform
        if self.streaming is not None:
            result['streaming'] = self.streaming
        if self.slurpable is not None:
            result['slurpable'] = self.slurpable
        if self.plugin is not None:
            result['plugin'] = self.plugin
        if self.name is not None:
            result['name'] = self.name
        return result


@dataclass
class ParserList:
    """
    Unified parser discovery result object.

    This is the single source of truth for parser metadata consumed by
    CLI help, --list-parsers output, Python API, and shell completions.

    All consumers use the same filtered data from this object, ensuring
    consistency across all interfaces.
    """
    parsers: List[ParserInfoType] = field(default_factory=list)
    filter: ParserFilter = field(default_factory=ParserFilter)
    show_hidden: bool = False
    show_deprecated: bool = False

    def __len__(self) -> int:
        return len(self.parsers)

    def __iter__(self) -> Iterator[ParserInfoType]:
        return iter(self.parsers)

    def __getitem__(self, index: int) -> ParserInfoType:
        return self.parsers[index]

    @classmethod
    def discover(
        cls,
        category: Optional[Union[str, List[str]]] = None,
        platform: Optional[Union[str, List[str]]] = None,
        streaming: Optional[bool] = None,
        slurpable: Optional[bool] = None,
        plugin: Optional[bool] = None,
        name: Optional[str] = None,
        show_hidden: bool = False,
        show_deprecated: bool = False
    ) -> 'ParserList':
        """
        Discover and filter parsers.

        Factory method that creates a ParserList with all matching parsers.
        This is the unified entrypoint for all parser discovery.

        Returns:
            ParserList: A ParserList object containing the filtered results.
        """
        if isinstance(category, str):
            category = [category]
        if isinstance(platform, str):
            platform = [platform]

        pfilter = ParserFilter(
            category=category,
            platform=platform,
            streaming=streaming,
            slurpable=slurpable,
            plugin=plugin,
            name=name
        )

        all_parsers = _get_raw_parser_info_list(
            show_hidden=show_hidden,
            show_deprecated=show_deprecated
        )

        filtered_parsers = [p for p in all_parsers if pfilter.matches(p)]

        return cls(
            parsers=filtered_parsers,
            filter=pfilter,
            show_hidden=show_hidden,
            show_deprecated=show_deprecated
        )

    def names(self) -> List[str]:
        """Return list of parser module names (for Python API)."""
        return [p['name'] for p in self.parsers]

    def arguments(self) -> List[str]:
        """Return list of CLI argument names (e.g., '--ls', '--dig')."""
        return [p['argument'] for p in self.parsers]

    def magic_commands(self) -> List[str]:
        """Return unique list of magic command names."""
        commands: List[str] = []
        for p in self.parsers:
            commands.extend(p.get('magic_commands', []))
        return sorted(list(set([c.split()[0] for c in commands])))

    def descriptions(self) -> List[str]:
        """Return list of 'argument:description' strings (for Zsh completion)."""
        return [
            f"'{p['argument']}:{p.get('description', 'No description')}'"
            for p in self.parsers
        ]

    def by_category(self) -> Dict[str, List[ParserInfoType]]:
        """Group parsers by category tags."""
        categories: Dict[str, List[ParserInfoType]] = {}
        for p in self.parsers:
            for tag in p.get('tags', []):
                if tag not in categories:
                    categories[tag] = []
                categories[tag].append(p)
        return categories

    def summary(self) -> Dict:
        """Return a summary of filter criteria and counts."""
        return {
            'total': len(self.parsers),
            'show_hidden': self.show_hidden,
            'show_deprecated': self.show_deprecated,
            'filter': self.filter.to_dict(),
            'count_by_category': {k: len(v) for k, v in self.by_category().items()},
            'streaming_count': sum(1 for p in self.parsers if p.get('streaming')),
            'slurpable_count': sum(1 for p in self.parsers if 'slurpable' in p.get('tags', [])),
            'plugin_count': sum(1 for p in self.parsers if p.get('plugin'))
        }

    def to_text(self, indent: int = 4, pad: int = 22) -> str:
        """Format as human-readable text for CLI help."""
        padding_char = ' '
        lines: List[str] = []
        for p in self.parsers:
            parser_arg = p.get('argument', 'UNKNOWN')
            padding = pad - len(parser_arg)
            parser_desc = p.get('description', 'No description available.')
            indent_text = padding_char * indent
            padding_text = padding_char * padding
            lines.append(f'{indent_text}{parser_arg}{padding_text}{parser_desc}')
        return '\n'.join(lines)

    def to_json(self, pretty: bool = False) -> str:
        """Format as JSON for scriptable consumption."""
        output: Dict = {
            'summary': self.summary(),
            'parsers': self.parsers
        }
        if pretty:
            return json.dumps(output, indent=2, ensure_ascii=False)
        return json.dumps(output, ensure_ascii=False)

    def to_yaml(self, pretty: bool = True) -> str:
        """Format as YAML for scriptable consumption."""
        output: Dict = {
            'summary': self.summary(),
            'parsers': self.parsers
        }
        try:
            from ruamel.yaml import YAML
            import io
            yaml = YAML()
            yaml.default_flow_style = not pretty
            yaml.allow_unicode = True
            yaml.explicit_start = pretty  # type: ignore
            yaml.encoding = 'utf-8'
            buf = io.BytesIO()
            yaml.dump(output, buf)
            return buf.getvalue().decode('utf-8')[:-1]
        except ImportError:
            utils.warning_message(['YAML Library not installed. Reverting to JSON output.'])
            return self.to_json(pretty=pretty)

    def to_dict(self) -> Dict:
        """Return raw dictionary representation."""
        return {
            'summary': self.summary(),
            'parsers': self.parsers
        }


__version__ = '1.25.6'

parsers: List[str] = [
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

def _cliname_to_modname(parser_cli_name: str) -> str:
    """Return real module name (dashes converted to underscores)"""
    return parser_cli_name.replace('--', '').replace('-', '_')

def _modname_to_cliname(parser_mod_name: str) -> str:
    """Return module's cli name (underscores converted to dashes)"""
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

# Create the local_parsers list. This is a list of custom or
# override parsers from <user_data_dir>/jc/jcparsers/*.py.
# Once this list is created, extend the parsers list with it.
local_parsers: List[str] = []
data_dir = appdirs.user_data_dir('jc', 'jc')  # type: ignore
local_parsers_dir = os.path.join(data_dir, 'jcparsers')
if os.path.isdir(local_parsers_dir):
    sys.path.append(data_dir)
    for name in os.listdir(local_parsers_dir):
        if _is_valid_parser_plugin(name, local_parsers_dir):
            plugin_name = name[0:-3]
            local_parsers.append(_modname_to_cliname(plugin_name))
            if plugin_name not in parsers:
                parsers.append(_modname_to_cliname(plugin_name))
    try:
        del name
    except Exception:
        pass

def _parser_argument(parser_mod_name: str) -> str:
    """Return short name of the parser with dashes and with -- prefix"""
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
    # ensure parser_mod_name is a true module name and not a cli name
    parser_mod_name = _cliname_to_modname(parser_mod_name)
    parser_cli_name = _modname_to_cliname(parser_mod_name)
    modpath: str = 'jcparsers.' if parser_cli_name in local_parsers else 'jc.parsers.'
    mod = None

    try:
        mod =  importlib.import_module(f'{modpath}{parser_mod_name}')
    except Exception as e:
        mod =  importlib.import_module(f'jc.parsers.disabled_parser')
        mod.__name__ = parser_mod_name
        utils.warning_message([f'"{parser_mod_name}" parser disabled due to error: {e}'])

    return mod

def _parser_is_slurpable(parser: ModuleType) -> bool:
    """
    Returns `True` if this parser can use the `--slurp` command option, else
    `False`

    parser is a parser module object.
    """
    tag_list = getattr(parser.info, 'tags', [])
    if 'slurpable' in tag_list:
        return True

    return False

def _parser_is_streaming(parser: ModuleType) -> bool:
    """
    Returns `True` if this is a streaming parser, else `False`

    parser is a parser module object.
    """
    if getattr(parser.info, 'streaming', None):
        return True

    return False

def _parser_is_hidden(parser: ModuleType) -> bool:
    """
    Returns `True` if this is a hidden parser, else `False`

    parser is a parser module object.
    """
    if getattr(parser.info, 'hidden', None):
        return True

    return False

def _parser_is_deprecated(parser: ModuleType) -> bool:
    """
    Returns `True` if this is a deprecated parser, else `False`

    parser is a parser module object.
    """
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
    plist = ParserList.discover(show_hidden=show_hidden, show_deprecated=show_deprecated)
    return plist.names()

def plugin_parser_mod_list(
    show_hidden: bool = False,
    show_deprecated: bool = False
) -> List[str]:
    """
    Returns a list of plugin parser module names. This function is a
    subset of `parser_mod_list()`.
    """
    plist = ParserList.discover(plugin=True, show_hidden=show_hidden, show_deprecated=show_deprecated)
    return plist.names()

def standard_parser_mod_list(
    show_hidden: bool = False,
    show_deprecated: bool = False
) -> List[str]:
    """
    Returns a list of standard parser module names. This function is a
    subset of `parser_mod_list()` and does not contain any streaming
    parsers.
    """
    plist = ParserList.discover(streaming=False, show_hidden=show_hidden, show_deprecated=show_deprecated)
    return plist.names()

def streaming_parser_mod_list(
    show_hidden: bool = False,
    show_deprecated: bool = False
) -> List[str]:
    """
    Returns a list of streaming parser module names. This function is a
    subset of `parser_mod_list()`.
    """
    plist = ParserList.discover(streaming=True, show_hidden=show_hidden, show_deprecated=show_deprecated)
    return plist.names()

def slurpable_parser_mod_list(
    show_hidden: bool = False,
    show_deprecated: bool = False
) -> List[str]:
    """
    Returns a list of slurpable parser module names. This function is a
    subset of `parser_mod_list()`.
    """
    plist = ParserList.discover(slurpable=True, show_hidden=show_hidden, show_deprecated=show_deprecated)
    return plist.names()

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

    if _modname_to_cliname(parser_mod_name) in local_parsers:
        info_dict['plugin'] = True

    if documentation:
        docs = parser_mod.__doc__
        if not docs:
            docs = 'No documentation available.\n'
        info_dict['documentation'] = docs

    return info_dict


def _get_raw_parser_info_list(
    show_hidden: bool = False,
    show_deprecated: bool = False
) -> List[ParserInfoType]:
    """
    Internal function to get raw parser info list without filters.
    This breaks the recursion cycle between ParserList.discover() and
    all_parser_info().
    """
    plist: List[str] = []
    for p in parsers:
        parser = get_parser(p)

        if not show_hidden and _parser_is_hidden(parser):
            continue

        if not show_deprecated and _parser_is_deprecated(parser):
            continue

        plist.append(p)

    return [parser_info(p, documentation=False) for p in plist]


def filter_parsers(
    parsers_list: Optional[List[ParserInfoType]] = None,
    category: Optional[Union[str, List[str]]] = None,
    platform: Optional[Union[str, List[str]]] = None,
    streaming: Optional[bool] = None,
    slurpable: Optional[bool] = None,
    plugin: Optional[bool] = None,
    name: Optional[str] = None,
    show_hidden: bool = False,
    show_deprecated: bool = False,
    return_list: bool = False
) -> Union[List[ParserInfoType], 'ParserList']:
    """
    Filter and return parser metadata based on various criteria.

    This is the unified parser discovery and filtering entrypoint used by
    CLI, Python API, and shell completion.

    All filter criteria are ANDed together. For list fields (category,
    platform), a parser matches if any of its values intersects with the
    filter values.

    Parameters:

        parsers_list:       (list)       Optional pre-fetched list of parser
                                         info dicts to filter. If not provided,
                                         all_parser_info() will be called.
        category:           (str/list)   Filter by category tags (e.g., 'command',
                                         'standard', 'generic', 'file', 'string',
                                         'binary', 'slurpable').
        platform:           (str/list)   Filter by compatible platforms (e.g.,
                                         'linux', 'darwin', 'win32', 'cygwin',
                                         'aix', 'freebsd').
        streaming:          (bool)        Filter by streaming capability.
        slurpable:          (bool)        Filter by slurp capability.
        plugin:             (bool)        Filter by local plugin (True) or
                                         built-in (False).
        name:               (str)         Filter by parser name substring.
        show_hidden:        (bool)        Include hidden parsers.
        show_deprecated:    (bool)        Include deprecated parsers.
        return_list:        (bool)        If True, return a ParserList object
                                         instead of a raw list of dicts.

    Returns:

        List[ParserInfoType] | ParserList: List of matching parser metadata
            dictionaries, or a ParserList object if return_list=True.

    Example:

        >>> import jc
        >>> # Find all Linux-compatible streaming parsers
        >>> streaming_linux = jc.filter_parsers(platform='linux', streaming=True)
        >>> # Find all slurpable command parsers
        >>> slurpable_cmd = jc.filter_parsers(category=['command'], slurpable=True)
        >>> # Get a ParserList object for advanced operations
        >>> plist = jc.filter_parsers(category='command', return_list=True)
        >>> print(plist.to_json(pretty=True))
    """
    if parsers_list is None:
        plist_obj = ParserList.discover(
            category=category,
            platform=platform,
            streaming=streaming,
            slurpable=slurpable,
            plugin=plugin,
            name=name,
            show_hidden=show_hidden,
            show_deprecated=show_deprecated
        )
        if return_list:
            return plist_obj
        return plist_obj.parsers

    if isinstance(category, str):
        category = [category]
    if isinstance(platform, str):
        platform = [platform]

    pfilter = ParserFilter(
        category=category,
        platform=platform,
        streaming=streaming,
        slurpable=slurpable,
        plugin=plugin,
        name=name
    )

    filtered = [p for p in parsers_list if pfilter.matches(p)]

    if return_list:
        return ParserList(
            parsers=filtered,
            filter=pfilter,
            show_hidden=show_hidden,
            show_deprecated=show_deprecated
        )

    return filtered


def all_parser_info(
    documentation: bool = False,
    show_hidden: bool = False,
    show_deprecated: bool = False,
    category: Optional[Union[str, List[str]]] = None,
    platform: Optional[Union[str, List[str]]] = None,
    streaming: Optional[bool] = None,
    slurpable: Optional[bool] = None,
    plugin: Optional[bool] = None,
    name: Optional[str] = None
) -> List[ParserInfoType]:
    """
    Returns a list of dictionaries that includes metadata for all parser
    modules. By default only non-hidden, non-deprecated parsers are
    returned.

    Additional filter parameters can be provided to narrow down results
    (see filter_parsers() for details).

    Parameters:

        documentation:      (boolean)    include parser docstrings if `True`
        show_hidden:        (boolean)    also show parsers marked as hidden
                                         in their info metadata.
        show_deprecated:    (boolean)    also show parsers marked as
                                         deprecated in their info metadata.
        category:           (str/list)   Filter by category tags.
        platform:           (str/list)   Filter by compatible platforms.
        streaming:          (bool)        Filter by streaming capability.
        slurpable:          (bool)        Filter by slurp capability.
        plugin:             (bool)        Filter by local plugin.
        name:               (str)         Filter by parser name substring.
    """
    if documentation:
        plist: List[str] = []
        for p in parsers:
            parser = get_parser(p)

            if not show_hidden and _parser_is_hidden(parser):
                continue

            if not show_deprecated and _parser_is_deprecated(parser):
                continue

            plist.append(p)

        p_info_list: List[ParserInfoType] = [parser_info(p, documentation=True) for p in plist]

        if category or platform or streaming is not None or \
           slurpable is not None or plugin is not None or name:
            p_info_list = filter_parsers(
                parsers_list=p_info_list,
                category=category,
                platform=platform,
                streaming=streaming,
                slurpable=slurpable,
                plugin=plugin,
                name=name
            )

        return p_info_list

    plist_obj = ParserList.discover(
        category=category,
        platform=platform,
        streaming=streaming,
        slurpable=slurpable,
        plugin=plugin,
        name=name,
        show_hidden=show_hidden,
        show_deprecated=show_deprecated
    )
    return plist_obj.parsers

def get_help(parser_mod_name: Union[str, ModuleType]) -> None:
    """
    Show help screen for the selected parser.

    This function will accept **module_name**, **cli-name**, and
    **--argument-name** variants of the module name string as well as a
    parser module object.
    """
    jc_parser = get_parser(parser_mod_name)
    help(jc_parser)
