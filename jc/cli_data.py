"""jc - JSON Convert cli_data module"""
from typing import List, Dict

long_options_map: Dict[str, List[str]] = {
    '--about': ['a', 'about jc'],
    '--filter-category': ['', 'filter parsers by category tags (comma-separated)'],
    '--filter-platform': ['', 'filter parsers by compatible platform (comma-separated)'],
    '--filter-streaming': ['', 'filter for streaming parsers only'],
    '--filter-no-streaming': ['', 'filter for non-streaming parsers only'],
    '--filter-slurpable': ['', 'filter for slurpable parsers only'],
    '--filter-no-slurpable': ['', 'filter for non-slurpable parsers only'],
    '--filter-plugin': ['', 'filter for local plugin parsers only'],
    '--filter-no-plugin': ['', 'filter for built-in parsers only'],
    '--filter-name': ['', 'filter parsers by name substring'],
    '--parser-format': ['', 'output format for parser listing: text (default), json, yaml'],
    '--force-color': ['C', 'force color output (overrides -m)'],
    '--debug': ['d', 'debug (double for verbose debug)'],
    '--help': ['h', 'help (--help --parser_name for parser documentation)'],
    '--list-parsers': ['', 'list available parsers (supports filters and --parser-format)'],
    '--monochrome': ['m', 'monochrome output'],
    '--meta-out': ['M', 'add metadata to output including timestamp, etc.'],
    '--pretty': ['p', 'pretty print output'],
    '--quiet': ['q', 'suppress warnings (double to ignore streaming errors)'],
    '--raw': ['r', 'raw output'],
    '--slurp': ['s', 'slurp multiple lines into an array'],
    '--unbuffer': ['u', 'unbuffer output'],
    '--version': ['v', 'version info'],
    '--yaml-out': ['y', 'YAML output'],
    '--bash-comp': ['B', 'gen Bash completion: jc -B > /etc/bash_completion.d/jc'],
    '--zsh-comp': ['Z', 'gen Zsh completion: jc -Z > "${fpath[1]}/_jc"']
}

new_pygments_colors: Dict[str, str] = {
    'black': 'ansiblack',
    'red': 'ansired',
    'green': 'ansigreen',
    'yellow': 'ansiyellow',
    'blue': 'ansiblue',
    'magenta': 'ansimagenta',
    'cyan': 'ansicyan',
    'gray': 'ansigray',
    'brightblack': 'ansibrightblack',
    'brightred': 'ansibrightred',
    'brightgreen': 'ansibrightgreen',
    'brightyellow': 'ansibrightyellow',
    'brightblue': 'ansibrightblue',
    'brightmagenta': 'ansibrightmagenta',
    'brightcyan': 'ansibrightcyan',
    'white': 'ansiwhite',
}

old_pygments_colors: Dict[str, str] = {
    'black': '#ansiblack',
    'red': '#ansidarkred',
    'green': '#ansidarkgreen',
    'yellow': '#ansibrown',
    'blue': '#ansidarkblue',
    'magenta': '#ansipurple',
    'cyan': '#ansiteal',
    'gray': '#ansilightgray',
    'brightblack': '#ansidarkgray',
    'brightred': '#ansired',
    'brightgreen': '#ansigreen',
    'brightyellow': '#ansiyellow',
    'brightblue': '#ansiblue',
    'brightmagenta': '#ansifuchsia',
    'brightcyan': '#ansiturquoise',
    'white': '#ansiwhite',
}

helptext_preamble_string: str = f'''\
jc converts the output of many commands, file-types, and strings to JSON or YAML

Usage:

    Standard syntax:

        COMMAND | jc [SLICE] [OPTIONS] PARSER

        cat FILE | jc [SLICE] [OPTIONS] PARSER

        echo STRING | jc [SLICE] [OPTIONS] PARSER

    Magic syntax:

        jc [SLICE] [OPTIONS] COMMAND

        jc [SLICE] [OPTIONS] /proc/<path-to-procfile>

    Parser discovery:

        jc parsers [FILTERS] [--parser-format FORMAT]
        jc --list-parsers [FILTERS] [--parser-format FORMAT]

        FORMAT: text (default), json, yaml
        Note: --format is deprecated, use --parser-format instead.

Parsers:
'''

slicetext_string: str = '''\
Slice:
    [start]:[end]

        start: [[-]index] - Zero-based start line, negative index for
                counting from the end

        end:   [[-]index] - Zero-based end line (excluding the index),
                negative index for counting from the end
'''

helptext_end_string: str = '''\
Examples:
    Standard Syntax:
        $ dig www.google.com | jc --pretty --dig
        $ cat /proc/meminfo | jc --pretty --proc

    Magic Syntax:
        $ jc --pretty dig www.google.com
        $ jc --pretty /proc/meminfo

    Line Slicing:
        $ cat output.txt | jc 4:15 --<PARSER>   # Parse from line 4 to 14
                                                # with <PARSER> (zero-based)

    Parser Documentation:
        $ jc --help --dig

    More Help:
        $ jc -hh          # show hidden parsers
        $ jc -hhh         # list parsers by category tags
'''