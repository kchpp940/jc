r"""jc - JSON Convert `rsync` command output streaming parser

> This streaming parser outputs JSON Lines (cli) or returns an Iterable of
> Dictionaries (module)

Supports the `-i` or `--itemize-changes` options with all levels of
verbosity. This parser will process the `STDOUT` output or a log file
generated with the `--log-file` option.

Usage (cli):

    $ rsync -i -a source/ dest | jc --rsync-s

or

    $ cat rsync-backup.log | jc --rsync-s

Usage (module):

    import jc

    result = jc.parse('rsync_s', rsync_command_output.splitlines())
    for item in result:
        # do something

Schema:

    {
      "type":                           string,       # 'file' or 'summary'
      "date":                           string,
      "time":                           string,
      "process":                        integer,
      "sent":                           integer,
      "received":                       integer,
      "total_size":                     integer,
      "matches":                        integer,
      "hash_hits":                      integer,
      "false_alarms":                   integer,
      "data":                           integer,
      "bytes_sec":                      float,
      "speedup":                        float,
      "filename":                       string,
      "date":                           string,
      "time":                           string,
      "process":                        integer,
      "metadata":                       string,
      "update_type":                    string/null,  # [0]
      "file_type":                      string/null,  # [1]
      "checksum_or_value_different":    bool/null,
      "size_different":                 bool/null,
      "modification_time_different":    bool/null,
      "permissions_different":          bool/null,
      "owner_different":                bool/null,
      "group_different":                bool/null,
      "acl_different":                  bool/null,
      "extended_attribute_different":   bool/null,
      "epoch":                          integer,      # [2]

      # below object only exists if using -qq or ignore_exceptions=True
      "_jc_meta": {
        "success":      boolean,     # false if error parsing
        "error":        string,      # exists if "success" is false
        "line":         string       # exists if "success" is false
      }
    }

    [0] 'file sent', 'file received', 'local change or creation',
        'hard link', 'not updated', 'message'
    [1] 'file', 'directory', 'symlink', 'device', 'special file'
    [2] naive timestamp if time and date fields exist and can be converted.

Examples:

    $ rsync -i -a source/ dest | jc --rsync-s
    {"type":"file","filename":"./","metadata":".d..t......","update_...}
    ...

    $ cat rsync_backup.log | jc --rsync-s
    {"type":"file","filename":"./","date":"2022/01/28","time":"03:53...}
    ...
"""
import re
from typing import Dict, Union
import jc.utils
from jc.streaming import streaming_parser, ParserState

class info():
    """Provides parser metadata (version, author, etc.)"""
    version = '1.3'
    description = '`rsync` command streaming parser'
    author = 'Kelly Brazil'
    author_email = 'kellyjonbrazil@gmail.com'
    compatible = ['linux', 'darwin', 'freebsd']
    tags = ['command']
    streaming = True


__version__ = info.version


def _process(proc_data: Dict) -> Dict:
    """
    Final processing to conform to the schema.

    Parameters:

        proc_data:   (Dictionary) raw structured data to process

    Returns:

        Dictionary. Structured data to conform to the schema.
    """
    int_list = {
        'process', 'sent', 'received', 'total_size', 'matches', 'hash_hits',
        'false_alarms', 'data'
    }

    float_list = {'bytes_sec', 'speedup'}

    for key in proc_data.copy():
        if key in int_list:
            proc_data[key] = jc.utils.convert_size_to_int(proc_data[key])

        if key in float_list:
            converted_val: Union[float, None] = None
            val = proc_data[key]
            if any([
                'K' in val,
                'M' in val,
                'G' in val,
                'T' in val
            ]):
                converted_int_val = jc.utils.convert_size_to_int(val)

                if not converted_int_val is None:
                    converted_val = float(converted_int_val)

            else:
                converted_val = jc.utils.convert_to_float(val)

            proc_data[key] = converted_val

        # add timestamp
        if 'date' in proc_data and 'time' in proc_data:
            date = proc_data['date'].replace('/', '-')
            date_time = f'{date} {proc_data["time"]}'
            ts = jc.utils.timestamp(date_time, format_hint=(7250,))
            proc_data['epoch'] = ts.naive

    return proc_data


_update_type = {
    '<': 'file sent',
    '>': 'file received',
    'c': 'local change or creation',
    'h': 'hard link',
    '.': 'not updated',
    '*': 'message',
    '+': None
}

_file_type = {
    'f': 'file',
    'd': 'directory',
    'L': 'symlink',
    'D': 'device',
    'S': 'special file',
    '+': None
}

_checksum_or_value_different = {'c': True, '.': False, '+': None, ' ': None, '?': None}
_size_different = {'s': True, '.': False, '+': None, ' ': None, '?': None}
_modification_time_different = {'t': True, '.': False, '+': None, ' ': None, '?': None}
_permissions_different = {'p': True, '.': False, '+': None, ' ': None, '?': None}
_owner_different = {'o': True, '.': False, '+': None, ' ': None, '?': None}
_group_different = {'g': True, '.': False, '+': None, ' ': None, '?': None}
_acl_different = {'a': True, '.': False, '+': None, ' ': None, '?': None}
_extended_attribute_different = {'x': True, '.': False, '+': None, ' ': None, '?': None}

_file_line_re = re.compile(r'(?P<meta>[<>ch.*][fdlDS][c.+ ?][s.+ ?][t.+ ?][p.+ ?][o.+ ?][g.+ ?][u.+ ?][a.+ ?][x.+ ?]) (?P<name>.+)')
_file_line_mac_re = re.compile(r'(?P<meta>[<>ch.*][fdlDS][c.+ ?][s.+ ?][t.+ ?][p.+ ?][o.+ ?][g.+ ?][x.+ ?]) (?P<name>.+)')
_stat1_line_re = re.compile(r'(sent)\s+(?P<sent>[0-9,]+)\s+(bytes)\s+(received)\s+(?P<received>[0-9,]+)\s+(bytes)\s+(?P<bytes_sec>[0-9,.]+)\s+(bytes/sec)')
_stat2_line_re = re.compile(r'(total size is)\s+(?P<total_size>[0-9,]+)\s+(speedup is)\s+(?P<speedup>[0-9,.]+)')
_stat1_line_simple_re = re.compile(r'(sent)\s+(?P<sent>[0-9,.TGMK]+)\s+(bytes)\s+(received)\s+(?P<received>[0-9,.TGMK]+)\s+(bytes)\s+(?P<bytes_sec>[0-9,.TGMK]+)\s+(bytes/sec)')
_stat2_line_simple_re = re.compile(r'(total\s+size\s+is)\s+(?P<total_size>[0-9,.TGMK]+)\s+(speedup\s+is)\s+(?P<speedup>[0-9,.TGMK]+)')
_file_line_log_re = re.compile(r'(?P<date>\d\d\d\d/\d\d/\d\d)\s+(?P<time>\d\d:\d\d:\d\d)\s+\[(?P<process>\d+)\]\s+(?P<meta>[<>ch.*][fdlDS][c.+ ?][s.+ ?][t.+ ?][p.+ ?][o.+ ?][g.+ ?][u.+ ?][a.+ ?][x.+ ?]) (?P<name>.+)')
_file_line_log_mac_re = re.compile(r'(?P<date>\d\d\d\d/\d\d/\d\d)\s+(?P<time>\d\d:\d\d:\d\d)\s+\[(?P<process>\d+)\]\s+(?P<meta>[<>ch.*][fdlDS][c.+ ?][s.+ ?][t.+ ?][p.+ ?][o.+ ?][g.+ ?][x.+ ?]) (?P<name>.+)')
_stat_line_log_re = re.compile(r'(?P<date>\d\d\d\d/\d\d/\d\d)\s+(?P<time>\d\d:\d\d:\d\d)\s+\[(?P<process>\d+)\]\s+sent\s+(?P<sent>[\d,]+)\s+bytes\s+received\s+(?P<received>[\d,]+)\s+bytes\s+total\s+size\s+(?P<total_size>[\d,]+)')
_stat1_line_log_v_re = re.compile(r'(?P<date>\d\d\d\d/\d\d/\d\d)\s+(?P<time>\d\d:\d\d:\d\d)\s+\[(?P<process>\d+)]\s+total:\s+matches=(?P<matches>[\d,]+)\s+hash_hits=(?P<hash_hits>[\d,]+)\s+false_alarms=(?P<false_alarms>[\d,]+)\s+data=(?P<data>[\d,]+)')
_stat2_line_log_v_re = re.compile(r'(?P<date>\d\d\d\d/\d\d/\d\d)\s+(?P<time>\d\d:\d\d:\d\d)\s+\[(?P<process>\d+)\]\s+sent\s+(?P<sent>[\d,]+)\s+bytes\s+received\s+(?P<received>[\d,]+)\s+bytes\s+(?P<bytes_sec>[\d,.]+)\s+bytes/sec')
_stat3_line_log_v_re = re.compile(r'(?P<date>\d\d\d\d/\d\d/\d\d)\s+(?P<time>\d\d:\d\d:\d\d)\s+\[(?P<process>\d+)]\s+total\s+size\s+is\s+(?P<total_size>[\d,]+)\s+speedup\s+is\s+(?P<speedup>[\d,.]+)')


def _init_state():
    return {'summary': {}, 'process': '', 'last_process': ''}


@streaming_parser(info, _process, _init_state, has_final_yield=True)
def parse(line, state, raw, quiet):
    """
    Main text parsing generator function. Returns an iterable object.

    Parameters:

        data:              (iterable)  line-based text data to parse
                                       (e.g. sys.stdin or str.splitlines())

        raw:               (boolean)   unprocessed output if True
        quiet:             (boolean)   suppress warning messages if True
        ignore_exceptions: (boolean)   ignore parsing exceptions if True

    Returns:

        Iterable of Dictionaries
    """
    summary = state['summary']
    process = state['process']
    last_process = state['last_process']

    if line is None:
        if state['summary']:
            result = state['summary']
            state['summary'] = {}
            return result
        return None

    if not line.strip():
        return None

    file_line = _file_line_re.match(line)
    if file_line:
        filename = file_line.group('name')
        meta = file_line.group('meta')
        return {
            'type': 'file',
            'filename': filename,
            'metadata': meta,
            'update_type': _update_type[meta[0]],
            'file_type': _file_type[meta[1]],
            'checksum_or_value_different': _checksum_or_value_different[meta[2]],
            'size_different': _size_different[meta[3]],
            'modification_time_different': _modification_time_different[meta[4]],
            'permissions_different': _permissions_different[meta[5]],
            'owner_different': _owner_different[meta[6]],
            'group_different': _group_different[meta[7]],
            'acl_different': _acl_different[meta[9]],
            'extended_attribute_different': _extended_attribute_different[meta[10]]
        }

    file_line_mac = _file_line_mac_re.match(line)
    if file_line_mac:
        filename = file_line_mac.group('name')
        meta = file_line_mac.group('meta')
        return {
            'type': 'file',
            'filename': filename,
            'metadata': meta,
            'update_type': _update_type[meta[0]],
            'file_type': _file_type[meta[1]],
            'checksum_or_value_different': _checksum_or_value_different[meta[2]],
            'size_different': _size_different[meta[3]],
            'modification_time_different': _modification_time_different[meta[4]],
            'permissions_different': _permissions_different[meta[5]],
            'owner_different': _owner_different[meta[6]],
            'group_different': _group_different[meta[7]]
        }

    file_line_log = _file_line_log_re.match(line)
    if file_line_log:
        results = []
        if process != last_process:
            if state['summary']:
                results.append(state['summary'])
            state['last_process'] = process
            state['summary'] = {}
        last_process = state['last_process']

        filename = file_line_log.group('name')
        date = file_line_log.group('date')
        time = file_line_log.group('time')
        process = file_line_log.group('process')
        meta = file_line_log.group('meta')
        state['process'] = process

        results.append({
            'type': 'file',
            'filename': filename,
            'date': date,
            'time': time,
            'process': process,
            'metadata': meta,
            'update_type': _update_type[meta[0]],
            'file_type': _file_type[meta[1]],
            'checksum_or_value_different': _checksum_or_value_different[meta[2]],
            'size_different': _size_different[meta[3]],
            'modification_time_different': _modification_time_different[meta[4]],
            'permissions_different': _permissions_different[meta[5]],
            'owner_different': _owner_different[meta[6]],
            'group_different': _group_different[meta[7]],
            'acl_different': _acl_different[meta[9]],
            'extended_attribute_different': _extended_attribute_different[meta[10]]
        })
        return results

    file_line_log_mac = _file_line_log_mac_re.match(line)
    if file_line_log_mac:
        results = []
        if process != last_process:
            if state['summary']:
                results.append(state['summary'])
            state['last_process'] = process
            state['summary'] = {}
        last_process = state['last_process']

        filename = file_line_log_mac.group('name')
        date = file_line_log_mac.group('date')
        time = file_line_log_mac.group('time')
        process = file_line_log_mac.group('process')
        meta = file_line_log_mac.group('meta')
        state['process'] = process

        results.append({
            'type': 'file',
            'filename': filename,
            'date': date,
            'time': time,
            'process': process,
            'metadata': meta,
            'update_type': _update_type[meta[0]],
            'file_type': _file_type[meta[1]],
            'checksum_or_value_different': _checksum_or_value_different[meta[2]],
            'size_different': _size_different[meta[3]],
            'modification_time_different': _modification_time_different[meta[4]],
            'permissions_different': _permissions_different[meta[5]],
            'owner_different': _owner_different[meta[6]],
            'group_different': _group_different[meta[7]]
        })
        return results

    stat1_line = _stat1_line_re.match(line)
    if stat1_line:
        state['summary'] = {
            'type': 'summary',
            'sent': stat1_line.group('sent'),
            'received': stat1_line.group('received'),
            'bytes_sec': stat1_line.group('bytes_sec')
        }
        return None

    stat2_line = _stat2_line_re.match(line)
    if stat2_line:
        state['summary']['total_size'] = stat2_line.group('total_size')
        state['summary']['speedup'] = stat2_line.group('speedup')
        return None

    stat1_line_simple = _stat1_line_simple_re.match(line)
    if stat1_line_simple:
        state['summary'] = {
            'type': 'summary',
            'sent': stat1_line_simple.group('sent'),
            'received': stat1_line_simple.group('received'),
            'bytes_sec': stat1_line_simple.group('bytes_sec')
        }
        return None

    stat2_line_simple = _stat2_line_simple_re.match(line)
    if stat2_line_simple:
        state['summary']['total_size'] = stat2_line_simple.group('total_size')
        state['summary']['speedup'] = stat2_line_simple.group('speedup')
        return None

    stat_line_log = _stat_line_log_re.match(line)
    if stat_line_log:
        state['summary'] = {
            'type': 'summary',
            'date': stat_line_log.group('date'),
            'time': stat_line_log.group('time'),
            'process': stat_line_log.group('process'),
            'sent': stat_line_log.group('sent'),
            'received': stat_line_log.group('received'),
            'total_size': stat_line_log.group('total_size')
        }
        return None

    stat1_line_log_v = _stat1_line_log_v_re.match(line)
    if stat1_line_log_v:
        state['summary'] = {
            'type': 'summary',
            'date': stat1_line_log_v.group('date'),
            'time': stat1_line_log_v.group('time'),
            'process': stat1_line_log_v.group('process'),
            'matches': stat1_line_log_v.group('matches'),
            'hash_hits': stat1_line_log_v.group('hash_hits'),
            'false_alarms': stat1_line_log_v.group('false_alarms'),
            'data': stat1_line_log_v.group('data')
        }
        return None

    stat2_line_log_v = _stat2_line_log_v_re.match(line)
    if stat2_line_log_v:
        state['summary']['sent'] = stat2_line_log_v.group('sent')
        state['summary']['received'] = stat2_line_log_v.group('received')
        state['summary']['bytes_sec'] = stat2_line_log_v.group('bytes_sec')
        return None

    stat3_line_log_v = _stat3_line_log_v_re.match(line)
    if stat3_line_log_v:
        state['summary']['total_size'] = stat3_line_log_v.group('total_size')
        state['summary']['speedup'] = stat3_line_log_v.group('speedup')
        return None
