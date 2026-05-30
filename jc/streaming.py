"""jc - JSON Convert streaming utils

This module provides the public infrastructure for streaming parsers:

- **StreamingContext**: composable state object that encapsulates five
  concerns as clear, reusable components:
    1. Success recording   — adds ``_jc_meta.success: True``
    2. Exception recording — creates ``_jc_meta`` with ``success: False``,
       ``error``, and ``line``
    3. Line-number tracking — tracks the current input line number
    4. Progress metadata    — tracks item count and provides progress info
    5. Exception handling   — decides whether to raise or yield on error
       (``ignore_exceptions`` behaviour)

- **@streaming_parser**: enhanced decorator that replaces ``@add_jc_meta``.
  It creates a ``StreamingContext``, validates input, and intercepts
  yields to attach ``_jc_meta`` automatically.

- **Backward-compatible helpers**: ``add_jc_meta``, ``raise_or_yield``,
  ``stream_success``, ``stream_error``, ``streaming_input_type_check``,
  ``streaming_line_input_type_check`` continue to work for legacy code.
"""

from functools import wraps
from typing import Tuple, Union, Iterable, Callable, TypeVar, cast, Any, Optional
from .jc_types import JSONDictType


F = TypeVar('F', bound=Callable[..., Any])

_IGNORE_EXCEPTIONS_MSG = '... Use the ignore_exceptions option (-qq) to ignore streaming parser errors.'


def streaming_input_type_check(data: Iterable[Union[str, bytes]]) -> None:
    """
    Ensure input data is an iterable, but not a string or bytes. Raises
    `TypeError` if not.
    """
    if not hasattr(data, '__iter__') or isinstance(data, (str, bytes)):
        raise TypeError("Input data must be a non-string iterable object.")


def streaming_line_input_type_check(line: str) -> None:
    """Ensure each line is a string. Raises `TypeError` if not."""
    if not isinstance(line, str):
        raise TypeError("Input line must be a 'str' object.")


def stream_success(
    output_line: JSONDictType,
    ignore_exceptions: bool,
    line_number: Optional[int] = None,
    progress: Optional[JSONDictType] = None
) -> JSONDictType:
    """Add `_jc_meta` object to output line if `ignore_exceptions=True`

    Parameters:

        output_line:       (Dict)  successfully parsed output line
        ignore_exceptions: (bool)  whether to add _jc_meta
        line_number:       (int)   optional line number for tracking
        progress:          (Dict)  optional progress metadata
    """
    if ignore_exceptions:
        meta: JSONDictType = {'success': True}
        if line_number is not None:
            meta['line_number'] = line_number
        if progress is not None:
            meta['progress'] = progress
        output_line['_jc_meta'] = meta

    return output_line


def stream_error(
    e: BaseException,
    line: str,
    line_number: Optional[int] = None,
    progress: Optional[JSONDictType] = None
) -> JSONDictType:
    """
    Return an error `_jc_meta` field.
    """
    meta: JSONDictType = {
        'success': False,
        'error': f'{e.__class__.__name__}: {e}',
        'line': line.strip()
    }
    if line_number is not None:
        meta['line_number'] = line_number
    if progress is not None:
        meta['progress'] = progress
    return {
        '_jc_meta': meta
    }


def add_jc_meta(func: F) -> F:
    """
    Decorator for streaming parsers to add `stream_success` and
    `stream_error` objects. This simplifies the `yield` lines in the
    streaming parsers.

    With the decorator on parse():

        # successfully parsed line:
        yield output_line if raw else _process(output_line)

        # unsuccessfully parsed line:
        except Exception as e:
            yield raise_or_yield(ignore_exceptions, e, line)

    Without the decorator on parse():

        # successfully parsed line:
        if raw:
            yield stream_success(output_line, ignore_exceptions)
        else:
            stream_success(_process(output_line), ignore_exceptions)

        # unsuccessfully parsed line:
        except Exception as e:
            yield stream_error(raise_or_yield(ignore_exceptions, e, line))

    In all cases above:

        output_line:  (Dict)  successfully parsed line yielded as a dict

        e:            (BaseException)  exception object as the first value
                      of the tuple if the line was not successfully parsed.

        line:         (str)  string of the original line that did not
                      successfully parse.

        ignore_exceptions:  (bool)  continue processing lines and ignore
                            exceptions if `True`.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        ignore_exceptions = kwargs.get('ignore_exceptions', False)
        ctx = kwargs.get('ctx')
        gen = func(*args, **kwargs)
        for value in gen:
            if isinstance(value, dict):
                if ctx is not None:
                    yield ctx.record_success(value)
                else:
                    yield stream_success(value, ignore_exceptions)
            else:
                exception_obj = value[0]
                line = value[1]
                if ctx is not None:
                    yield ctx.record_error(exception_obj, line)
                else:
                    yield stream_error(exception_obj, line)

    return cast(F, wrapper)


def raise_or_yield(
    ignore_exceptions: bool,
    e: BaseException,
    line: str
) -> Tuple[BaseException, str]:
    """
    Return the exception object and line string if `ignore_exceptions` is
    `True`. Otherwise, re-raise the exception from the exception object with
    an annotation.
    """
    if not ignore_exceptions:
        e.args = (str(e) + _IGNORE_EXCEPTIONS_MSG,)
        raise e

    return e, line


class StreamingContext:
    """Composable state object for streaming parsers.

    Encapsulates five concerns as clear, reusable components:

    1. **Success recording** — ``record_success()`` adds ``_jc_meta``
       with ``success: True`` (and optional line_number / progress).
    2. **Exception recording** — ``record_error()`` creates ``_jc_meta``
       with ``success: False``, ``error``, ``line``.
    3. **Line-number tracking** — ``check_line()`` validates each input
       line and increments the line counter.
    4. **Progress metadata** — ``progress`` property returns a dict with
       ``line_number`` and ``item_count`` when enabled.
    5. **Exception handling** — ``handle_exception()`` decides whether to
       raise or return the error tuple based on ``ignore_exceptions``.

    Parsers receive this object from the ``@streaming_parser`` decorator
    instead of managing the above states individually.

    Parameters:

        raw:                (bool)  if True, skip ``_process()`` calls
        quiet:              (bool)  suppress warning messages
        ignore_exceptions:  (bool)  continue on errors if True
        track_line_number:  (bool)  include line_number in _jc_meta
        track_progress:     (bool)  include progress dict in _jc_meta
    """

    def __init__(
        self,
        raw: bool = False,
        quiet: bool = False,
        ignore_exceptions: bool = False,
        track_line_number: bool = False,
        track_progress: bool = False,
    ):
        self.raw = raw
        self.quiet = quiet
        self.ignore_exceptions = ignore_exceptions
        self._track_line_number = track_line_number
        self._track_progress = track_progress
        self.line_number: int = 0
        self.item_count: int = 0

    # ── Line-number tracking ────────────────────────────────────────

    def check_line(self, line: str) -> str:
        """Validate input line type and advance line counter.

        Calls ``streaming_line_input_type_check`` and increments
        ``self.line_number``.
        """
        streaming_line_input_type_check(line)
        self.line_number += 1
        return line

    # ── Progress metadata ───────────────────────────────────────────

    @property
    def progress(self) -> Optional[JSONDictType]:
        """Return progress metadata dict, or ``None`` if tracking is off."""
        if not self._track_progress:
            return None
        return {
            'line_number': self.line_number,
            'item_count': self.item_count,
        }

    def _line_number_for_meta(self) -> Optional[int]:
        """Return line_number for metadata, or ``None`` if not tracking."""
        if self._track_line_number or self._track_progress:
            return self.line_number
        return None

    def _progress_for_meta(self) -> Optional[JSONDictType]:
        """Return progress for metadata, or ``None`` if not tracking."""
        if self._track_progress:
            return self.progress
        return None

    # ── Success recording ───────────────────────────────────────────

    def record_success(self, output_line: JSONDictType) -> JSONDictType:
        """Add ``_jc_meta`` success metadata to *output_line*.

        Called automatically by the ``@streaming_parser`` decorator; parsers
        should not need to invoke this directly.
        """
        return stream_success(
            output_line,
            self.ignore_exceptions,
            line_number=self._line_number_for_meta(),
            progress=self._progress_for_meta(),
        )

    # ── Exception recording ─────────────────────────────────────────

    def record_error(self, e: BaseException, line: str) -> JSONDictType:
        """Create ``_jc_meta`` error record.

        Called automatically by the ``@streaming_parser`` decorator; parsers
        should not need to invoke this directly.
        """
        return stream_error(
            e, line,
            line_number=self._line_number_for_meta(),
            progress=self._progress_for_meta(),
        )

    # ── Exception handling (ignore_exceptions behaviour) ─────────────

    def handle_exception(
        self, e: BaseException, line: str
    ) -> Tuple[BaseException, str]:
        """Decide whether to raise or return the exception.

        If ``ignore_exceptions`` is ``False``, re-raises with an
        annotation.  Otherwise returns ``(exception, line)`` for the
        decorator to turn into an error record.
        """
        return raise_or_yield(self.ignore_exceptions, e, line)

    # ── Output emission ─────────────────────────────────────────────

    def emit(
        self,
        output_line: JSONDictType,
        process_fn: Optional[Callable[[JSONDictType], JSONDictType]] = None
    ) -> JSONDictType:
        """Prepare an output line for yielding.

        Applies *process_fn* when not in raw mode and increments the
        item counter.  The ``@streaming_parser`` decorator then adds
        ``_jc_meta`` automatically.

        Usage inside a parser::

            yield ctx.emit(output_line, _process)
        """
        if not self.raw and process_fn is not None:
            output_line = process_fn(output_line)
        self.item_count += 1
        return output_line


def streaming_parser(func: F) -> F:
    """Enhanced decorator for streaming parsers.

    Replaces ``@add_jc_meta`` and provides a ``StreamingContext`` to the
    wrapped function so that the parser only needs to handle input
    splitting and field parsing logic.

    The decorator:

    1. Calls ``streaming_input_type_check(data)``.
    2. Creates a ``StreamingContext`` and injects it as the ``ctx``
       keyword argument.
    3. Intercepts yields from the wrapped generator:
       - ``dict`` → attaches ``_jc_meta`` success record via
         ``ctx.record_success()``.
       - ``(BaseException, str)`` tuple → attaches ``_jc_meta`` error
         record via ``ctx.record_error()``.

    Parsers using this decorator replace their boilerplate with::

        @streaming_parser
        def parse(data, raw=False, quiet=False, ignore_exceptions=False, ctx=None):
            jc.utils.compatibility(__name__, info.compatible, quiet)

            for line in data:
                try:
                    ctx.check_line(line)
                    output_line = {}
                    # … parser-specific field extraction …
                    yield ctx.emit(output_line, _process)
                except Exception as e:
                    yield ctx.handle_exception(e, line)

    Parameters accepted by the decorated function (unchanged externally):

        data:              (iterable)  line-based text data to parse
        raw:               (boolean)   unprocessed output if True
        quiet:             (boolean)   suppress warning messages if True
        ignore_exceptions: (boolean)   ignore parsing exceptions if True

    Extra keyword arguments consumed by the decorator:

        track_line_number: (boolean)   include line_number in _jc_meta
        track_progress:    (boolean)   include progress dict in _jc_meta
    """
    @wraps(func)
    def wrapper(
        data,
        raw: bool = False,
        quiet: bool = False,
        ignore_exceptions: bool = False,
        **kwargs
    ):
        streaming_input_type_check(data)

        track_line_number = kwargs.pop('track_line_number', False)
        track_progress = kwargs.pop('track_progress', False)

        ctx = StreamingContext(
            raw=raw,
            quiet=quiet,
            ignore_exceptions=ignore_exceptions,
            track_line_number=track_line_number,
            track_progress=track_progress,
        )

        gen = func(
            data,
            raw=raw,
            quiet=quiet,
            ignore_exceptions=ignore_exceptions,
            ctx=ctx,
            **kwargs,
        )

        for value in gen:
            if isinstance(value, dict):
                yield ctx.record_success(value)
            else:
                exception_obj = value[0]
                line = value[1]
                yield ctx.record_error(exception_obj, line)

    return cast(F, wrapper)
