"""jc - JSON Convert parser registry module

Single source of truth for parser discovery, loading, disable state,
and built-in override detection.  Every consumer — CLI ``--about``,
shell completion, ``parser_info()``, … — reads from the one
``ParserRegistry`` instance exported as ``registry``.
"""
import sys
import os
import re
import importlib
from typing import List, Dict, Set, Optional, Union
from types import ModuleType
from jc import appdirs
from jc import utils


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


def cliname_to_modname(parser_cli_name: str) -> str:
    return parser_cli_name.replace('--', '').replace('-', '_')


def modname_to_cliname(parser_mod_name: str) -> str:
    return parser_mod_name.replace('_', '-')


class ParserRegistry:
    """Single source of truth for parser discovery, loading, and state.

    Responsibilities
    ----------------
    * Discover plugin parsers in ``<user_data_dir>/jc/jcparsers/*.py``
    * Load and cache their module objects (one import, no re-import)
    * Read user-managed ``disabled_parsers.txt`` to skip selected plugins
    * Track which plugins **override** a built-in parser of the same name
    * Track which plugins failed validation or import (**broken**)
    * Emit warnings for overrides, disabled, and broken plugins

    All consumers (CLI ``--about``, shell completion, ``parser_info``,
    …) should read from the same ``ParserRegistry`` instance.
    """

    DISABLED_FILE = 'disabled_parsers.txt'

    def __init__(self) -> None:
        self._parsers: List[str] = list(_BUILTIN_PARSERS)
        self._plugin_parsers: List[str] = []
        self._disabled_parsers: Set[str] = set()
        self._overridden_parsers: Set[str] = set()
        self._broken_parsers: Set[str] = set()
        self._modules: Dict[str, ModuleType] = {}
        self._data_dir: str = appdirs.user_data_dir('jc', 'jc')
        self._local_parsers_dir: str = os.path.join(self._data_dir, 'jcparsers')
        self._disabled_file: str = os.path.join(self._data_dir, self.DISABLED_FILE)
        self._user_disabled: Set[str] = set()
        self._load_user_disabled()
        self._discover()

    def _load_user_disabled(self) -> None:
        if not os.path.isfile(self._disabled_file):
            return
        try:
            with open(self._disabled_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        cliname = modname_to_cliname(
                            cliname_to_modname(line.replace('--', ''))
                        )
                        self._user_disabled.add(cliname)
        except Exception as e:
            utils.warning_message([
                f'Could not read {self._disabled_file}: {e}'
            ])

    def _discover(self) -> None:
        if not os.path.isdir(self._local_parsers_dir):
            return

        sys.path.append(self._data_dir)

        for name in sorted(os.listdir(self._local_parsers_dir)):
            if not (re.match(r'\w+\.py$', name) and
                    os.path.isfile(os.path.join(self._local_parsers_dir, name))):
                continue

            plugin_mod_name = cliname_to_modname(name[0:-3])
            cliname = modname_to_cliname(plugin_mod_name)

            if cliname in self._user_disabled:
                self._disabled_parsers.add(cliname)
                utils.warning_message([
                    f'Plugin parser "{cliname}" is disabled in {self._disabled_file}'
                ])
                continue

            try:
                mod = importlib.import_module(f'jcparsers.{plugin_mod_name}')
                if not (hasattr(mod, 'info') and hasattr(mod, 'parse')):
                    utils.warning_message([
                        f'Not installing invalid parser plugin "{plugin_mod_name}" at {self._local_parsers_dir}'
                    ])
                    self._broken_parsers.add(cliname)
                    self._disabled_parsers.add(cliname)
                    del mod
                    continue
                self._modules[cliname] = mod
            except Exception as e:
                utils.warning_message([
                    f'Not installing parser plugin "{plugin_mod_name}" at {self._local_parsers_dir} due to error: {e}'
                ])
                self._broken_parsers.add(cliname)
                self._disabled_parsers.add(cliname)
                continue

            self._plugin_parsers.append(cliname)

            if cliname in self._parsers:
                self._overridden_parsers.add(cliname)
                utils.warning_message([
                    f'Plugin parser "{cliname}" overrides the built-in parser of the same name'
                ])
            else:
                self._parsers.append(cliname)

    # ── read-only properties ──────────────────────────────────────────

    @property
    def parsers(self) -> List[str]:
        return self._parsers

    @property
    def plugin_parsers(self) -> List[str]:
        return self._plugin_parsers

    @property
    def disabled_parsers(self) -> Set[str]:
        return self._disabled_parsers

    @property
    def overridden_parsers(self) -> Set[str]:
        return self._overridden_parsers

    @property
    def broken_parsers(self) -> Set[str]:
        return self._broken_parsers

    @property
    def user_disabled_parsers(self) -> Set[str]:
        return self._user_disabled

    # ── query helpers ─────────────────────────────────────────────────

    def is_plugin(self, cliname: str) -> bool:
        return cliname in self._plugin_parsers

    def is_overridden(self, cliname: str) -> bool:
        return cliname in self._overridden_parsers

    def is_disabled(self, cliname: str) -> bool:
        return cliname in self._disabled_parsers

    def is_broken(self, cliname: str) -> bool:
        return cliname in self._broken_parsers

    def is_user_disabled(self, cliname: str) -> bool:
        return cliname in self._user_disabled

    # ── module cache ──────────────────────────────────────────────────

    def get_cached_module(self, cliname: str) -> Optional[ModuleType]:
        return self._modules.get(cliname)

    def cache_module(self, cliname: str, mod: ModuleType) -> None:
        self._modules[cliname] = mod

    def mark_disabled(self, cliname: str) -> None:
        self._disabled_parsers.add(cliname)


registry = ParserRegistry()
