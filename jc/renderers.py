"""jc - JSON Convert output renderers module

Defines unified interfaces for output rendering, error wrapping, and meta injection.
All output paths (JSON, YAML, NDJSON, streaming, --meta-out, -qq errors) flow through
these interfaces, with the CLI only responsible for selecting strategies.
"""

import io
import sys
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TextIO, Union

from .jc_types import JSONDictType, CustomColorType

PYGMENTS_INSTALLED: bool = False
try:
    import pygments
    from pygments import highlight
    from pygments.style import Style
    from pygments.lexers.data import JsonLexer, YamlLexer
    from pygments.formatters import Terminal256Formatter
    PYGMENTS_INSTALLED = True
except Exception:
    pass

YAML_INSTALLED: bool = False
try:
    from ruamel.yaml import YAML, representer
    YAML_INSTALLED = True
except Exception:
    pass


@dataclass
class RenderingContext:
    """Context data passed through the rendering pipeline.

    Carries all non-data information needed for rendering decisions,
    keeping the data objects pure and context-free.
    """
    parser_name: Optional[str] = None
    run_timestamp: Optional[datetime] = None
    slice_start: Optional[int] = None
    slice_end: Optional[int] = None
    magic_command: Optional[List[str]] = None
    magic_command_exit: Optional[int] = None
    input_list: Optional[List[str]] = None
    pretty: bool = False
    ascii_only: bool = False
    mono: bool = False
    unbuffer: bool = False
    custom_colors: CustomColorType = field(default_factory=dict)
    json_indent: Optional[int] = None
    json_separators: Optional[tuple[str, str]] = (',', ':')


class OutputFormatter(ABC):
    """Interface for formatting data structures to output strings.

    Implementations handle the serialization of Python data structures
    to their target string formats (JSON, YAML, NDJSON).
    """

    @abstractmethod
    def format(self, data: Any, ctx: RenderingContext) -> str:
        """Format data to string representation."""
        ...

    @abstractmethod
    def format_streaming(self, data: Any, ctx: RenderingContext) -> str:
        """Format a single streaming record to string representation."""
        ...


class MetaInjector(ABC):
    """Interface for injecting metadata into data structures.

    Implementations add _jc_meta fields to data objects based on
    the rendering context.
    """

    @abstractmethod
    def inject(self, data: Any, ctx: RenderingContext) -> Any:
        """Inject metadata into data, returning the modified data."""
        ...


class ErrorWrapper(ABC):
    """Interface for wrapping exceptions into error data objects.

    Implementations convert exceptions into structured error objects
    suitable for output formatting.
    """

    @abstractmethod
    def wrap(self, error: BaseException, line: Optional[str], ctx: RenderingContext) -> JSONDictType:
        """Wrap an exception into an error data object."""
        ...


class JsonFormatter(OutputFormatter):
    """JSON output formatter with optional syntax highlighting."""

    @staticmethod
    def _string_serializer(data: Any) -> str:
        return str(data)

    def _apply_highlighting(self, json_str: str, ctx: RenderingContext) -> str:
        if not ctx.mono and PYGMENTS_INSTALLED:
            class JcStyle(Style):
                styles: CustomColorType = ctx.custom_colors
            return str(highlight(json_str, JsonLexer(), Terminal256Formatter(style=JcStyle))[0:-1])
        return json_str

    def format(self, data: Any, ctx: RenderingContext) -> str:
        if ctx.pretty:
            ctx.json_indent = 2
            ctx.json_separators = None

        j_string = json.dumps(
            data,
            indent=ctx.json_indent,
            separators=ctx.json_separators,
            ensure_ascii=ctx.ascii_only,
            default=self._string_serializer
        )
        return self._apply_highlighting(j_string, ctx)

    def format_streaming(self, data: Any, ctx: RenderingContext) -> str:
        j_string = json.dumps(
            data,
            ensure_ascii=ctx.ascii_only,
            default=self._string_serializer
        )
        return self._apply_highlighting(j_string, ctx)


class YamlFormatter(OutputFormatter):
    """YAML output formatter with optional syntax highlighting."""

    def _apply_highlighting(self, yaml_str: str, ctx: RenderingContext) -> str:
        if not ctx.mono and PYGMENTS_INSTALLED:
            class JcStyle(Style):
                styles: CustomColorType = ctx.custom_colors
            return str(highlight(yaml_str, YamlLexer(), Terminal256Formatter(style=JcStyle))[0:-1])
        return yaml_str

    def format(self, data: Any, ctx: RenderingContext) -> str:
        if not YAML_INSTALLED:
            from . import utils
            utils.warning_message(['YAML Library not installed. Reverting to JSON output.'])
            return JsonFormatter().format(data, ctx)

        YAML.official_plug_ins = lambda a: []
        representer.RoundTripRepresenter.ignore_aliases = lambda x, y: True

        yaml = YAML()
        yaml.default_flow_style = False
        yaml.explicit_start = True
        yaml.allow_unicode = not ctx.ascii_only
        yaml.encoding = 'utf-8'

        y_string_buf = io.BytesIO()
        yaml.dump(data, y_string_buf)
        y_string = y_string_buf.getvalue().decode('utf-8')[:-1]

        return self._apply_highlighting(y_string, ctx)

    def format_streaming(self, data: Any, ctx: RenderingContext) -> str:
        return self.format(data, ctx)


class NdjsonFormatter(OutputFormatter):
    """Newline-Delimited JSON formatter for streaming output."""

    def format(self, data: Any, ctx: RenderingContext) -> str:
        if isinstance(data, list):
            return '\n'.join(JsonFormatter().format_streaming(item, ctx) for item in data)
        return JsonFormatter().format_streaming(data, ctx)

    def format_streaming(self, data: Any, ctx: RenderingContext) -> str:
        return JsonFormatter().format_streaming(data, ctx)


class NoopMetaInjector(MetaInjector):
    """Meta injector that does nothing (default behavior)."""

    def inject(self, data: Any, ctx: RenderingContext) -> Any:
        return data


class MetaOutInjector(MetaInjector):
    """Injects --meta-out metadata into output data."""

    def _build_meta_obj(self, ctx: RenderingContext) -> JSONDictType:
        meta_obj: JSONDictType = {
            'parser': ctx.parser_name,
            'timestamp': ctx.run_timestamp.timestamp() if ctx.run_timestamp else None,
            'slice_start': ctx.slice_start,
            'slice_end': ctx.slice_end
        }

        if ctx.magic_command:
            meta_obj['magic_command'] = ctx.magic_command
            meta_obj['magic_command_exit'] = ctx.magic_command_exit

        if ctx.input_list:
            meta_obj['input_list'] = ctx.input_list

        return meta_obj

    def inject(self, data: Any, ctx: RenderingContext) -> Any:
        if ctx.run_timestamp is None:
            ctx.run_timestamp = datetime.now(timezone.utc)

        meta_obj = self._build_meta_obj(ctx)

        if isinstance(data, dict):
            if '_jc_meta' not in data:
                data['_jc_meta'] = {}
            data['_jc_meta'].update(meta_obj)

        elif isinstance(data, list):
            if not data:
                data.append({})
            for item in data:
                if isinstance(item, dict):
                    if '_jc_meta' not in item:
                        item['_jc_meta'] = {}
                    item['_jc_meta'].update(meta_obj)

        return data


class StreamingMetaInjector(MetaInjector):
    """Injects streaming success/failure metadata into output."""

    def __init__(self, ignore_exceptions: bool = False):
        self.ignore_exceptions = ignore_exceptions

    def inject(self, data: Any, ctx: RenderingContext) -> Any:
        if self.ignore_exceptions and isinstance(data, dict):
            if '_jc_meta' not in data:
                data['_jc_meta'] = {}
            if 'success' not in data['_jc_meta']:
                data['_jc_meta']['success'] = True
        return data


class StreamingErrorWrapper(ErrorWrapper):
    """Wraps streaming parser errors into error objects for -qq mode."""

    def wrap(self, error: BaseException, line: Optional[str], ctx: RenderingContext) -> JSONDictType:
        error_obj: JSONDictType = {
            '_jc_meta': {
                'success': False,
                'error': f'{error.__class__.__name__}: {error}',
            }
        }
        if line is not None:
            error_obj['_jc_meta']['line'] = line.strip()
        return error_obj


class OutputRenderer:
    """Composes formatter, meta injector, and error wrapper into a pipeline.

    This is the main entry point for output rendering. The CLI selects
    the appropriate components based on command-line options, and this
    class orchestrates the rendering pipeline.
    """

    def __init__(
        self,
        formatter: OutputFormatter,
        meta_injector: MetaInjector = NoopMetaInjector(),
        error_wrapper: Optional[ErrorWrapper] = None,
    ) -> None:
        self.formatter = formatter
        self.meta_injector = meta_injector
        self.error_wrapper = error_wrapper
        self._ascii_mode = False

    def render(self, data: Any, ctx: RenderingContext) -> str:
        """Render data through the full pipeline: meta inject → format."""
        data = self.meta_injector.inject(data, ctx)
        ctx.ascii_only = ctx.ascii_only or self._ascii_mode
        try:
            return self.formatter.format(data, ctx)
        except UnicodeEncodeError:
            self._ascii_mode = True
            ctx.ascii_only = True
            return self.formatter.format(data, ctx)

    def render_streaming(self, data: Any, ctx: RenderingContext) -> str:
        """Render a single streaming record through the pipeline."""
        data = self.meta_injector.inject(data, ctx)
        ctx.ascii_only = ctx.ascii_only or self._ascii_mode
        try:
            return self.formatter.format_streaming(data, ctx)
        except UnicodeEncodeError:
            self._ascii_mode = True
            ctx.ascii_only = True
            return self.formatter.format_streaming(data, ctx)

    def render_error(self, error: BaseException, line: Optional[str], ctx: RenderingContext) -> str:
        """Render an error through the pipeline: wrap → format."""
        if self.error_wrapper is None:
            raise error
        error_data = self.error_wrapper.wrap(error, line, ctx)
        return self.render_streaming(error_data, ctx)

    def print(self, data: Any, ctx: RenderingContext, file: TextIO = sys.stdout) -> None:
        """Render and print data safely, handling encoding issues."""
        from . import utils
        output = self.render(data, ctx)
        utils._safe_print(output, flush=ctx.unbuffer, file=file)

    def print_streaming(self, data: Any, ctx: RenderingContext, file: TextIO = sys.stdout) -> None:
        """Render and print a streaming record safely."""
        from . import utils
        output = self.render_streaming(data, ctx)
        utils._safe_print(output, flush=ctx.unbuffer, file=file)

    def print_error(self, error: BaseException, line: Optional[str], ctx: RenderingContext, file: TextIO = sys.stdout) -> None:
        """Render and print an error safely."""
        from . import utils
        output = self.render_error(error, line, ctx)
        utils._safe_print(output, flush=ctx.unbuffer, file=file)


def create_renderer(
    yaml_output: bool = False,
    meta_out: bool = False,
    ignore_exceptions: bool = False,
    streaming: bool = False,
) -> OutputRenderer:
    """Factory function to create the appropriate renderer based on CLI options.

    This is the bridge between CLI option parsing and the rendering strategy.
    The CLI calls this with its parsed options and receives a configured
    OutputRenderer ready for use.
    """
    if streaming:
        formatter: OutputFormatter = NdjsonFormatter()
    elif yaml_output:
        formatter = YamlFormatter()
    else:
        formatter = JsonFormatter()

    if meta_out:
        meta_injector: MetaInjector = MetaOutInjector()
    elif streaming and ignore_exceptions:
        meta_injector = StreamingMetaInjector(ignore_exceptions=True)
    else:
        meta_injector = NoopMetaInjector()

    error_wrapper: Optional[ErrorWrapper] = None
    if streaming and ignore_exceptions:
        error_wrapper = StreamingErrorWrapper()

    return OutputRenderer(
        formatter=formatter,
        meta_injector=meta_injector,
        error_wrapper=error_wrapper,
    )
