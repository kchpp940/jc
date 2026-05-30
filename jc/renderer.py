"""jc - JSON Convert unified output renderer module"""

import io
import sys
import json
from typing import Any, Iterator, Iterable, List, Dict, Optional, Union

from .jc_types import JSONDictType, CustomColorType
from . import utils

PYGMENTS_INSTALLED: bool = False
try:
    import pygments
    from pygments import highlight
    from pygments.style import Style
    from pygments.token import (Name, Number, String, Keyword)
    from pygments.lexers.data import JsonLexer, YamlLexer
    from pygments.formatters import Terminal256Formatter
    PYGMENTS_INSTALLED = True
except Exception:
    pass

OUTPUT_JSON = 'json'
OUTPUT_YAML = 'yaml'
OUTPUT_NDJSON = 'ndjson'

VALID_OUTPUT_FORMATS = (OUTPUT_JSON, OUTPUT_YAML, OUTPUT_NDJSON)

STREAMING_ITEM_WARN_DEFAULT: int = 1000


def _string_serializer(data: Any) -> str:
    return str(data)


def _yaml_available() -> bool:
    try:
        from ruamel.yaml import YAML
        return True
    except Exception:
        return False


class OutputRenderer:
    """
    Unified output renderer for JSON, YAML, and NDJSON formats.

    This class encapsulates all output formatting logic so that standard
    parsers, streaming parsers, slurp mode, and error objects all use the
    same formatting pipeline.

    Args:
        output_format: One of 'json', 'yaml', or 'ndjson'
        pretty: Whether to pretty-print (only affects JSON/YAML)
        mono: Whether to use monochrome (no ANSI color codes)
        ascii_only: Whether to escape non-ASCII characters
        unbuffer: Whether to flush after each print
        custom_colors: Pygments custom color dictionary for syntax highlighting
    """

    __slots__ = (
        '_output_format',
        '_pretty',
        '_mono',
        '_ascii_only',
        '_unbuffer',
        '_custom_colors',
        '_json_indent',
        '_json_separators',
        '_streaming_item_warn',
        '_streaming_item_limit',
    )

    def __init__(
        self,
        output_format: str = OUTPUT_JSON,
        pretty: bool = False,
        mono: bool = False,
        ascii_only: bool = False,
        unbuffer: bool = False,
        custom_colors: Optional[CustomColorType] = None,
        streaming_item_warn: Optional[int] = STREAMING_ITEM_WARN_DEFAULT,
        streaming_item_limit: Optional[int] = None,
    ) -> None:
        if output_format not in VALID_OUTPUT_FORMATS:
            raise ValueError(
                f"Invalid output_format: {output_format}. "
                f"Must be one of {VALID_OUTPUT_FORMATS}"
            )

        self._output_format = output_format
        self._pretty = pretty
        self._mono = mono
        self._ascii_only = ascii_only
        self._unbuffer = unbuffer
        self._custom_colors = custom_colors or {}
        self._streaming_item_warn = streaming_item_warn
        self._streaming_item_limit = streaming_item_limit

        if self._pretty:
            self._json_indent = 2
            self._json_separators = None
        else:
            self._json_indent = None
            self._json_separators = (',', ':')

        if self._output_format == OUTPUT_NDJSON:
            self._mono = True

    @property
    def output_format(self) -> str:
        return self._output_format

    @property
    def mono(self) -> bool:
        return self._mono

    def _render_json(self, data: Any) -> str:
        j_string = json.dumps(
            data,
            indent=self._json_indent,
            separators=self._json_separators,
            ensure_ascii=self._ascii_only,
            default=_string_serializer
        )

        if not self._mono and PYGMENTS_INSTALLED and self._custom_colors:
            class JcStyle(Style):
                styles: CustomColorType = self._custom_colors

            return str(highlight(j_string, JsonLexer(), Terminal256Formatter(style=JcStyle))[0:-1])

        return j_string

    def _render_yaml(self, data: Any) -> str:
        if not _yaml_available():
            utils.warning_message(['YAML Library not installed. Reverting to JSON output.'])
            return self._render_json(data)

        from ruamel.yaml import YAML, representer

        y_string_buf = io.BytesIO()

        YAML.official_plug_ins = lambda a: []
        representer.RoundTripRepresenter.ignore_aliases = lambda x, y: True

        yaml = YAML()
        yaml.default_flow_style = False
        yaml.explicit_start = True
        yaml.allow_unicode = not self._ascii_only
        yaml.encoding = 'utf-8'
        yaml.dump(data, y_string_buf)
        y_string = y_string_buf.getvalue().decode('utf-8')[:-1]

        if not self._mono and PYGMENTS_INSTALLED and self._custom_colors:
            class JcStyle(Style):
                styles: CustomColorType = self._custom_colors

            return str(highlight(y_string, YamlLexer(), Terminal256Formatter(style=JcStyle))[0:-1])

        return y_string

    def _render_ndjson(self, data: Any) -> str:
        if isinstance(data, list):
            lines = []
            for item in data:
                lines.append(json.dumps(
                    item,
                    separators=(',', ':'),
                    ensure_ascii=self._ascii_only,
                    default=_string_serializer
                ))
            return '\n'.join(lines)

        return json.dumps(
            data,
            separators=(',', ':'),
            ensure_ascii=self._ascii_only,
            default=_string_serializer
        )

    def render(self, data: Any) -> str:
        """
        Render data to the configured output format.

        Args:
            data: The data to render (dict, list, or any JSON-serializable type)

        Returns:
            Formatted string in the configured output format
        """
        if self._output_format == OUTPUT_NDJSON:
            return self._render_ndjson(data)
        elif self._output_format == OUTPUT_YAML:
            return self._render_yaml(data)
        else:
            return self._render_json(data)

    def safe_print(self, data: Any) -> None:
        """
        Safely print rendered data, handling UnicodeEncodeError by falling
        back to ASCII-only output.

        Args:
            data: The data to render and print
        """
        try:
            print(self.render(data), flush=self._unbuffer)
        except UnicodeEncodeError:
            self._ascii_only = True
            print(self.render(data), flush=self._unbuffer)

    def render_iter(self, items: Iterable[Any]) -> Iterator[str]:
        """
        Render an iterable of data items as a streaming output.

        Format-specific behavior:
          - NDJSON: yields one compact JSON line per item immediately
            (true streaming, O(1) memory per item, no thresholds applied)
          - JSON: collects all items into a list, then yields the
            rendered array as a single string (correct array structure).
            Emits a warning if item count exceeds streaming_item_warn
            and raises MemoryError if it exceeds streaming_item_limit.
          - YAML: collects all items into a list, then yields the
            rendered YAML document as a single string. Same thresholds
            as JSON.

        Args:
            items: An iterable of data items (typically dicts from a
                   streaming parser)

        Yields:
            Formatted strings, one per NDJSON line, or a single string
            for JSON/YAML array output

        Raises:
            MemoryError: If streaming_item_limit is set and the number
                         of collected items exceeds it (JSON/YAML only)
        """
        if self._output_format == OUTPUT_NDJSON:
            for item in items:
                yield json.dumps(
                    item,
                    separators=(',', ':'),
                    ensure_ascii=self._ascii_only,
                    default=_string_serializer
                )
        else:
            collected: List[Any] = []
            warned = False
            for item in items:
                collected.append(item)
                count = len(collected)

                if self._streaming_item_limit is not None and count > self._streaming_item_limit:
                    raise MemoryError(
                        f"Streaming output collected {count} items, exceeding the "
                        f"limit of {self._streaming_item_limit}. "
                        f"Use --ndjson-out (-n) for true streaming output with O(1) memory."
                    )

                if not warned and self._streaming_item_warn is not None and count > self._streaming_item_warn:
                    warned = True
                    utils.warning_message([
                        f"Streaming output has collected {count} items into memory for {self._output_format.upper()} array assembly.",
                        "For large streaming data, use --ndjson-out (-n) for true O(1) memory streaming."
                    ])

            yield self.render(collected)

    def safe_print_iter(self, items: Iterable[Any]) -> None:
        """
        Safely print an iterable of data items as streaming output,
        handling UnicodeEncodeError by falling back to ASCII-only output.

        For NDJSON, each item is printed immediately on its own line
        with per-item Unicode fallback.
        For JSON/YAML, all items are collected first (with threshold
        checks) and printed as a single formatted array with a single
        Unicode fallback pass.
        """
        if self._output_format == OUTPUT_NDJSON:
            for item in items:
                try:
                    line = json.dumps(
                        item,
                        separators=(',', ':'),
                        ensure_ascii=self._ascii_only,
                        default=_string_serializer
                    )
                    print(line, flush=self._unbuffer)
                except UnicodeEncodeError:
                    self._ascii_only = True
                    line = json.dumps(
                        item,
                        separators=(',', ':'),
                        ensure_ascii=self._ascii_only,
                        default=_string_serializer
                    )
                    print(line, flush=self._unbuffer)
        else:
            collected: List[Any] = []
            warned = False
            for item in items:
                collected.append(item)
                count = len(collected)

                if self._streaming_item_limit is not None and count > self._streaming_item_limit:
                    raise MemoryError(
                        f"Streaming output collected {count} items, exceeding the "
                        f"limit of {self._streaming_item_limit}. "
                        f"Use --ndjson-out (-n) for true streaming output with O(1) memory."
                    )

                if not warned and self._streaming_item_warn is not None and count > self._streaming_item_warn:
                    warned = True
                    utils.warning_message([
                        f"Streaming output has collected {count} items into memory for {self._output_format.upper()} array assembly.",
                        "For large streaming data, use --ndjson-out (-n) for true O(1) memory streaming."
                    ])

            try:
                print(self.render(collected), flush=self._unbuffer)
            except UnicodeEncodeError:
                self._ascii_only = True
                print(self.render(collected), flush=self._unbuffer)
