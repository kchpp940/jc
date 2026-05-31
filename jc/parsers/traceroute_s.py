r"""jc - JSON Convert `traceroute` command output streaming parser

> This streaming parser outputs JSON Lines (cli) or returns an Iterable of
> Dictionaries (module)

Supports `traceroute` and `traceroute6` output.

> Note: On some operating systems you will need to redirect `STDERR` to
> `STDOUT` for destination info since the header line is sent to
> `STDERR`. A warning message will be printed to `STDERR` if the
> header row is not found.
>
> e.g. `$ traceroute 8.8.8.8 2>&1 | jc --traceroute-s`

Usage (cli):

    $ traceroute 1.2.3.4 | jc --traceroute-s

Usage (module):

    import jc
    result = jc.parse('traceroute_s', traceroute_command_output.splitlines())
    for item in result:
        # do something

Schema:

    {
      # 'header' or 'hop'
      "type":                 string,

      # 'header' type has the fields below:
      "destination_ip":       string,
      "destination_name":     string,
      "max_hops":             integer,
      "data_bytes":           integer,

      # 'hop' type has the fields below:
      "hop":                  integer,
      "probes": [
        {
          "annotation":       string,
          "asn":              integer,
          "ip":               string,
          "name":             string,
          "rtt":              float
        }
      ]

      # below object only exists if using -qq or ignore_exceptions=True
      "_jc_meta": {
        "success":            boolean,  # false if error parsing
        "error":              string,   # exists if "success" is false
        "line":               string    # exists if "success" is false
      }
    }

Examples:

    $ traceroute google.com | jc --traceroute-s -p
    {
      "type": "header",
      "destination_ip": "216.58.194.46",
      "destination_name": "google.com",
      "max_hops": 30,
      "data_bytes": 60
    }
    {
      "type": "hop",
      "hop": 1,
      "probes": [
        {
          "annotation": null,
          "asn": null,
          "ip": "216.230.231.141",
          "name": "216-230-231-141.static.houston.tx.oplink.net",
          "rtt": 198.574
        },
        {
          "annotation": null,
          "asn": null,
          "ip": "216.230.231.141",
          "name": "216-230-231-141.static.houston.tx.oplink.net",
          "rtt": null
        },
        {
          "annotation": null,
          "asn": null,
          "ip": "216.230.231.141",
          "name": "216-230-231-141.static.houston.tx.oplink.net",
          "rtt": 198.65
        }
      ]
    }
    ...

    $ traceroute google.com  | jc --traceroute-s -p -r
    {
      "type": "header",
      "destination_ip": "216.58.194.46",
      "destination_name": "google.com",
      "max_hops": "30",
      "data_bytes": "60"
    }
    {
      "type": "hop",
      "hop": "1",
      "probes": [
        {
          "annotation": null,
          "asn": null,
          "ip": "216.230.231.141",
          "name": "216-230-231-141.static.houston.tx.oplink.net",
          "rtt": "198.574"
        },
        {
          "annotation": null,
          "asn": null,
          "ip": "216.230.231.141",
          "name": "216-230-231-141.static.houston.tx.oplink.net",
          "rtt": null
        },
        {
          "annotation": null,
          "asn": null,
          "ip": "216.230.231.141",
          "name": "216-230-231-141.static.houston.tx.oplink.net",
          "rtt": "198.650"
        }
      ]
    }
    ...
"""
from jc.exceptions import ParseError
from jc.streaming import streaming_parser
from .traceroute import RE_HEADER, RE_HOP, RE_HEADER_HOPS_BYTES, _Hop, _loads, _process, _serialize_hop


class info():
    """Provides parser metadata (version, author, etc.)"""
    version = '1.0'
    description = '`traceroute` and `traceroute6` command streaming parser'
    author = 'Shintaro Kojima'
    author_email = 'goodies@codeout.net'
    compatible = ['linux', 'darwin', 'freebsd']
    tags = ['command']
    streaming = True


__version__ = info.version

'''
Copyright (C) 2015 Luis Benitez

Parses the output of a traceroute execution into an AST (Abstract Syntax Tree).

The MIT License (MIT)

Copyright (c) 2014 Luis Benitez

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''


def _init_state():
    return {'hop_cache': None}


@streaming_parser(info, _process, _init_state, has_final_yield=True)
def parse(line, state, raw, quiet):
    """
    Main text parsing function. Returns an iterable object.

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
        if state['hop_cache']:
            result = {'type': 'hop', **_serialize_hop(state['hop_cache'])}
            state['hop_cache'] = None
            return result
        return None

    if RE_HEADER.search(line):
        tr = _loads(line, quiet)
        return {
            'type': 'header',
            'destination_ip': tr.dest_ip,
            'destination_name': tr.dest_name,
            'max_hops': tr.max_hops,
            'data_bytes': tr.data_bytes
        }

    m = RE_HOP.match(line)
    if not m:
        return None

    if not m.group(1):
        if not state['hop_cache']:
            raise ParseError('No hop index found')
        line = f"{state['hop_cache'].idx} {line}"
        tr = _loads(line, quiet=True)
        if not tr.hops:
            return None
        state['hop_cache'].probes.extend(tr.hops[0].probes)
        return None

    result = None
    if state['hop_cache']:
        result = {'type': 'hop', **_serialize_hop(state['hop_cache'])}
    tr = _loads(line, quiet=True)
    if not tr.hops:
        state['hop_cache'] = None
        return result
    state['hop_cache'] = tr.hops[0]
    return result
