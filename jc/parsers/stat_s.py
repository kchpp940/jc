r"""jc - JSON Convert `stat` command output streaming parser

> This streaming parser outputs JSON Lines (cli) or returns an Iterable of
> Dictionaries (module)

The `xxx_epoch` calculated timestamp fields are naive. (i.e. based on the
local time of the system the parser is run on).

The `xxx_epoch_utc` calculated timestamp fields are timezone-aware and are
only available if the timezone field is UTC.

Usage (cli):

    $ stat * | jc --stat-s

Usage (module):

    import jc

    result = jc.parse('stat_s', stat_command_output.splitlines())
    for item in result:
        # do something

Schema:

    {
      "file":                     string,
      "link_to"                   string,
      "size":                     integer,
      "blocks":                   integer,
      "io_blocks":                integer,
      "type":                     string,
      "device":                   string,
      "inode":                    integer,
      "links":                    integer,
      "access":                   string,
      "flags":                    string,
      "uid":                      integer,
      "user":                     string,
      "gid":                      integer,
      "group":                    string,
      "access_time":              string,    # - = null
      "access_time_epoch":        integer,   # naive timestamp
      "access_time_epoch_utc":    integer,   # timezone-aware timestamp
      "modify_time":              string,    # - = null
      "modify_time_epoch":        integer,   # naive timestamp
      "modify_time_epoch_utc":    integer,   # timezone-aware timestamp
      "change_time":              string,    # - = null
      "change_time_epoch":        integer,   # naive timestamp
      "change_time_epoch_utc":    integer,   # timezone-aware timestamp
      "birth_time":               string,    # - = null
      "birth_time_epoch":         integer,   # naive timestamp
      "birth_time_epoch_utc":     integer,   # timezone-aware timestamp
      "unix_device":              integer,
      "rdev":                     integer,
      "block_size":               integer,
      "unix_flags":               string,

      # below object only exists if using -qq or ignore_exceptions=True
      "_jc_meta": {
        "success":                boolean,   # false if error parsing
        "error":                  string,    # exists if "success" is false
        "line":                   string     # exists if "success" is false
      }
    }

Examples:

    $ stat | jc --stat-s
    {"file":"(stdin)","unix_device":1027739696,"inode":1155,"flags":"cr...}

    $ stat | jc --stat-s -r
    {"file":"(stdin)","unix_device":"1027739696","inode":"1155","flag...}
"""
import shlex
import jc.utils
from jc.streaming import streaming_parser
from jc.jc_types import JSONDictType
from jc.exceptions import ParseError


class info():
    """Provides parser metadata (version, author, etc.)"""
    version = '1.3'
    description = '`stat` command streaming parser'
    author = 'Kelly Brazil'
    author_email = 'kellyjonbrazil@gmail.com'
    compatible = ['linux', 'darwin', 'freebsd']
    tags = ['command']
    streaming = True


__version__ = info.version


def _process(proc_data: JSONDictType) -> JSONDictType:
    """
    Final processing to conform to the schema.

    Parameters:

        proc_data:   (Dictionary) raw structured data to process

    Returns:

        Dictionary. Structured data to conform to the schema.
    """
    int_list: set[str] = {'size', 'blocks', 'io_blocks', 'inode', 'links', 'uid', 'gid',
                'unix_device', 'rdev', 'block_size'}

    null_list: set[str] = {'access_time', 'modify_time', 'change_time', 'birth_time'}

    for key in proc_data.copy():
        if key in int_list:
            proc_data[key] = jc.utils.convert_to_int(proc_data[key])

        # turn - into null for time fields and add calculated timestamp fields
        if key in null_list:
            if proc_data[key] == '-':
                proc_data[key] = None

            ts_string = proc_data[key]
            if isinstance(ts_string, str) or ts_string is None:
                ts = jc.utils.timestamp(ts_string, format_hint=(7100, 7200))
                proc_data[key + '_epoch'] = ts.naive
                proc_data[key + '_epoch_utc'] = ts.utc

    return proc_data


def _init_state():
    return {'output_line': {}, 'os_type': ''}


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
    if line is None:
        if state['output_line']:
            result = state['output_line']
            state['output_line'] = {}
            return result
        return None

    line = line.rstrip()
    if not line.strip():
        return None

    if line.startswith('  File: '):
        state['os_type'] = 'linux'
    os_type = state['os_type']

    if os_type == 'linux':
        if line.startswith('  File: '):
            result = None
            if state['output_line']:
                result = state['output_line']
            state['output_line'] = {}
            line_list = line.split(maxsplit=1)
            state['output_line']['file'] = line_list[1]
            if ' -> ' in state['output_line']['file']:
                filename = state['output_line']['file'].split(' -> ')[0].strip('\u2018').rstrip('\u2019')
                link = state['output_line']['file'].split(' -> ')[1].strip('\u2018').rstrip('\u2019')
                state['output_line']['file'] = filename
                state['output_line']['link_to'] = link
            else:
                filename = state['output_line']['file'].split(' -> ')[0].strip('\u2018').rstrip('\u2019')
                state['output_line']['file'] = filename
            return result

        if line.startswith('  Size: '):
            line_list = line.split(maxsplit=7)
            state['output_line']['size'] = line_list[1]
            state['output_line']['blocks'] = line_list[3]
            state['output_line']['io_blocks'] = line_list[6]
            state['output_line']['type'] = line_list[7]
            return None

        if line.startswith('Device: '):
            line_list = line.split()
            state['output_line']['device'] = line_list[1]
            state['output_line']['inode'] = line_list[3]
            state['output_line']['links'] = line_list[5]
            return None

        if line.startswith('Access: ('):
            line = line.replace('(', ' ').replace(')', ' ').replace('/', ' ')
            line_list = line.split()
            state['output_line']['access'] = line_list[1]
            state['output_line']['flags'] = line_list[2]
            state['output_line']['uid'] = line_list[4]
            state['output_line']['user'] = line_list[5]
            state['output_line']['gid'] = line_list[7]
            state['output_line']['group'] = line_list[8]
            return None

        if line.startswith('Context: '):
            return None

        if line.startswith('Access: 2'):
            line_list = line.split(maxsplit=1)
            state['output_line']['access_time'] = line_list[1]
            return None

        if line.startswith('Modify: '):
            line_list = line.split(maxsplit=1)
            state['output_line']['modify_time'] = line_list[1]
            return None

        if line.startswith('Change: '):
            line_list = line.split(maxsplit=1)
            state['output_line']['change_time'] = line_list[1]
            return None

        if line.startswith(' Birth: '):
            line_list = line.split(maxsplit=1)
            state['output_line']['birth_time'] = line_list[1]
            return None

        raise ParseError('Not stat data')

    if os_type != 'linux':
        value = shlex.split(line)
        if not value[0].isdigit() or not value[1].isdigit():
            raise ParseError('Not stat data')
        output_line = {
            'file': ' '.join(value[15:]),
            'unix_device': value[0],
            'inode': value[1],
            'flags': value[2],
            'links': value[3],
            'user': value[4],
            'group': value[5],
            'rdev': value[6],
            'size': value[7],
            'access_time': value[8],
            'modify_time': value[9],
            'change_time': value[10],
            'birth_time': value[11],
            'block_size': value[12],
            'blocks': value[13],
            'unix_flags': value[14]
        }
        state['output_line'] = {}
        return output_line

    raise ParseError('Not stat data')
