import os
import sys
import re
import shlex
from dataclasses import dataclass, field
from typing import List, Optional
from copy import deepcopy

from .lib import all_parser_info, parsers
from . import utils
from .cli_data import long_options_map

SLICER_PATTERN: str = r'-?[0-9]*\:-?[0-9]*$'
SLICER_RE = re.compile(SLICER_PATTERN)

PYGMENTS_INSTALLED: bool = False
try:
    from pygments.token import (Name, Number, String, Keyword)
    PYGMENTS_INSTALLED = True
except Exception:
    pass

try:
    import pygments
    from .cli_data import new_pygments_colors, old_pygments_colors
    if pygments.__version__.startswith('2.3.'):
        PYGMENT_COLOR = old_pygments_colors
    else:
        PYGMENT_COLOR = new_pygments_colors
except Exception:
    pass


@dataclass(frozen=True)
class MagicParseResult:
    found_parser: Optional[str] = None
    options: List[str] = field(default_factory=list)
    run_command: Optional[List[str]] = None
    run_command_str: str = ''
    slice_str: str = ''


@dataclass(frozen=True)
class SlicerOptions:
    slice_str: str = ''
    slice_start: Optional[int] = None
    slice_end: Optional[int] = None


@dataclass(frozen=True)
class ParserOptions:
    raw: bool = False
    quiet: bool = False
    ignore_exceptions: bool = False
    slurp: bool = False
    meta_out: bool = False
    unbuffer: bool = False


@dataclass(frozen=True)
class OutputOptions:
    pretty: bool = False
    yaml_output: bool = False


@dataclass
class RuntimeOutputConfig:
    mono: bool = False
    custom_colors: dict = field(default_factory=dict)
    ascii_only: bool = False
    json_separators: Optional[tuple[str, str]] = (',', ':')
    json_indent: Optional[int] = None

    def update_mono(self, options: List[str], force_color: bool) -> None:
        self.mono = ('m' in options or bool(os.getenv('NO_COLOR'))) and not force_color
        if not sys.stdout.isatty() and not force_color:
            self.mono = True
        if not PYGMENTS_INSTALLED:
            self.mono = True

    def update_custom_colors(self) -> None:
        if not PYGMENTS_INSTALLED:
            return

        input_error = False
        env_colors = os.getenv('JC_COLORS')

        if env_colors:
            color_list = env_colors.split(',')
        else:
            color_list = ['default', 'default', 'default', 'default']

        if len(color_list) != 4:
            input_error = True

        for color in color_list:
            if color != 'default' and color not in PYGMENT_COLOR:
                input_error = True

        if input_error:
            utils.warning_message(['Could not parse JC_COLORS environment variable'])
            color_list = ['default', 'default', 'default', 'default']

        self.custom_colors = {
            Name.Tag: f'bold {PYGMENT_COLOR[color_list[0]]}' if color_list[0] != 'default' else f"bold {PYGMENT_COLOR['blue']}",
            Keyword: PYGMENT_COLOR[color_list[1]] if color_list[1] != 'default' else PYGMENT_COLOR['brightblack'],
            Number: PYGMENT_COLOR[color_list[2]] if color_list[2] != 'default' else PYGMENT_COLOR['magenta'],
            String: PYGMENT_COLOR[color_list[3]] if color_list[3] != 'default' else PYGMENT_COLOR['green']
        }


@dataclass(frozen=True)
class DisplayOptions:
    about: bool = False
    help_me: bool = False
    show_hidden: bool = False
    show_categories: bool = False
    version_info: bool = False


@dataclass(frozen=True)
class DebugOptions:
    debug: bool = False
    verbose_debug: bool = False
    force_color: bool = False


@dataclass(frozen=True)
class CompletionOptions:
    bash_comp: bool = False
    zsh_comp: bool = False


@dataclass(frozen=True)
class CliParseResult:
    argv: List[str] = field(default_factory=list)
    options: List[str] = field(default_factory=list)
    parser_name: Optional[str] = None
    magic: MagicParseResult = field(default_factory=MagicParseResult)
    slicer: SlicerOptions = field(default_factory=SlicerOptions)
    parser_opts: ParserOptions = field(default_factory=ParserOptions)
    display: DisplayOptions = field(default_factory=DisplayOptions)
    debug: DebugOptions = field(default_factory=DebugOptions)
    completion: CompletionOptions = field(default_factory=CompletionOptions)

    @staticmethod
    def _parse_magic_syntax(args: List[str]) -> MagicParseResult:
        found_parser = None
        options: List[str] = []
        run_command: Optional[List[str]] = None
        run_command_str: str = ''
        slice_str: str = ''

        if len(args) <= 1 or (args[1].startswith('--') and args[1] not in long_options_map):
            return MagicParseResult()

        args_given: List[str] = args[1:]

        for arg in list(args_given):
            if arg in long_options_map:
                options.extend(long_options_map[arg][0])
                args_given.pop(0)
                continue

            if arg.startswith('--'):
                options = []
                return MagicParseResult()

            if ':' in arg:
                if SLICER_RE.match(arg):
                    slice_str = arg
                    args_given.pop(0)
                    continue
                else:
                    utils.warning_message(['Invalid slice syntax.'])
                    args_given.pop(0)
                    continue

            if arg.startswith('-'):
                options.extend(args_given.pop(0)[1:])
                continue

            break

        if len(args_given) == 0:
            options = []
            return MagicParseResult()

        magic_dict: dict[str, str] = {}
        for entry in all_parser_info():
            magic_dict.update({mc: entry['argument'] for mc in entry.get('magic_commands', [])})

        run_command = args_given

        if run_command:
            try:
                run_command_str = shlex.join(run_command)
            except AttributeError:
                run_command_str = ' '.join(run_command)

        one_word_command: str = run_command[0]
        two_word_command: str = ' '.join(run_command[0:2])
        found_parser = magic_dict.get(two_word_command, magic_dict.get(one_word_command))

        return MagicParseResult(
            found_parser=found_parser,
            options=options,
            run_command=run_command,
            run_command_str=run_command_str,
            slice_str=slice_str
        )

    @staticmethod
    def _parser_shortname(parser_arg: str) -> str:
        p = parser_arg.lstrip('-')
        return p.replace('_', '-')

    @classmethod
    def _find_parser_name(cls, args: List[str], magic_parser: Optional[str]) -> Optional[str]:
        if magic_parser:
            return cls._parser_shortname(magic_parser)

        for arg in args:
            parser_name: str = cls._parser_shortname(arg)
            if parser_name in parsers:
                return parser_name

        return None

    @classmethod
    def from_argv(cls, argv: List[str]) -> 'CliParseResult':
        magic = cls._parse_magic_syntax(argv)

        options: List[str] = []
        options.extend(magic.options)

        slice_str = magic.slice_str

        if not magic.found_parser:
            for opt in argv:
                if SLICER_RE.match(opt):
                    slice_str = opt

                if opt in long_options_map:
                    options.extend(long_options_map[opt][0])

                if opt.startswith('-') and not opt.startswith('--'):
                    options.extend(opt[1:])

        slice_start = None
        slice_end = None
        if slice_str:
            slice_start_str, slice_end_str = slice_str.split(':', maxsplit=1)
            if slice_start_str:
                slice_start = int(slice_start_str)
            if slice_end_str:
                slice_end = int(slice_end_str)

        slicer = SlicerOptions(
            slice_str=slice_str,
            slice_start=slice_start,
            slice_end=slice_end
        )

        parser_opts = ParserOptions(
            raw='r' in options,
            quiet='q' in options,
            ignore_exceptions=options.count('q') > 1,
            slurp='s' in options,
            meta_out='M' in options,
            unbuffer='u' in options
        )

        display = DisplayOptions(
            about='a' in options,
            help_me='h' in options,
            show_hidden=options.count('h') > 1,
            show_categories=options.count('h') > 2,
            version_info='v' in options
        )

        debug = DebugOptions(
            debug='d' in options,
            verbose_debug=options.count('d') > 1,
            force_color='C' in options
        )

        completion = CompletionOptions(
            bash_comp='B' in options,
            zsh_comp='Z' in options
        )

        parser_name = cls._find_parser_name(argv, magic.found_parser)

        return cls(
            argv=deepcopy(argv),
            options=options,
            parser_name=parser_name,
            magic=magic,
            slicer=slicer,
            parser_opts=parser_opts,
            display=display,
            debug=debug,
            completion=completion
        )

    def derive_output_options(self) -> OutputOptions:
        return OutputOptions(
            pretty='p' in self.options,
            yaml_output='y' in self.options
        )

    def create_runtime_config(self) -> RuntimeOutputConfig:
        config = RuntimeOutputConfig()
        config.update_mono(self.options, self.debug.force_color)
        config.update_custom_colors()
        return config
