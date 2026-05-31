r"""jc - JSON Convert `foo` command output streaming parser

> This streaming parser outputs JSON Lines (cli) or returns an Iterable of
> Dictionaries (module)

<<Short foo description and caveats>>

Usage (cli):

    $ foo | jc --foo-s

Usage (module):

    import jc

    result = jc.parse('foo_s', foo_command_output.splitlines())
    for item in result:
        # do something

Schema:

    {
      "foo":            string,

      # below object only exists if using -qq or ignore_exceptions=True
      "_jc_meta": {
        "success":      boolean,
        "error":        string,
        "line":         string
      }
    }

Examples:

    $ foo | jc --foo-s
    {example output}
    ...

    $ foo | jc --foo-s -r
    {example output}
    ...
"""
from typing import Dict, Optional
from jc.streaming import streaming_parser, ParserState
from jc.jc_types import JSONDictType
from jc.exceptions import ParseError


class info():
    """Parser metadata."""
    version = '1.0'
    description = '`foo` command streaming parser'
    author = 'John Doe'
    author_email = 'johndoe@gmail.com'
    # details = 'enter any other details here'

    # compatible options: linux, darwin, cygwin, win32, aix, freebsd
    compatible = ['linux', 'darwin', 'cygwin', 'win32', 'aix', 'freebsd']

    # tags options: generic, standard, file, string, binary, command, slurpable
    tags = ['command']

    # required for streaming parsers
    streaming = True

    # other attributes - only enable if needed
    deprecated = False
    hidden = False


__version__ = info.version


def _process(proc_data: JSONDictType) -> JSONDictType:
    """
    Final processing to conform to the schema.

    Parameters:

        proc_data:   (Dictionary) raw structured data to process

    Returns:

        Dictionary. Structured data to conform to the schema.
    """
    # add semantic conversions using jc.utils helpers
    return proc_data


def _init_state() -> ParserState:
    """
    Initialize parser state. Omit for stateless parsers.
    """
    return {
        'header_found': False,
        'line_count': 0
    }


@streaming_parser(info, _process, _init_state)
def parse(
    line: Optional[str],
    state: ParserState,
    raw: bool,
    quiet: bool
) -> Optional[JSONDictType]:
    """
    Line parsing function. Decorator handles iteration and meta.

    Returns:
        Dict:   Output parsed result for this line
        None:   Skip this line (accumulate state)
    """
    state['line_count'] += 1

    output_line: Dict = {}

    if not line.strip():
        return None

    # parse content here — use jc.utils and jc.parsers.universal helpers
    # output_line = {'field1': line.split()[0], 'field2': line.split()[1]}

    if output_line:
        return output_line
    else:
        raise ParseError('Not foo data')
