"""jc - JSON Convert streaming utils"""

import inspect
from functools import wraps
from typing import Tuple, Union, Iterable, Callable, TypeVar, cast, Any, Optional
from .jc_types import JSONDictType


F = TypeVar('F', bound=Callable[..., Any])


class _LineTracker:
    """Wraps a data iterable and tracks line numbers/ranges for ``_jc_meta``.

    Each consumed lines are numbered from caller (slicer) to parser so the
    ``add_jc_meta`` decorator can discover which input lines produced each
    output dict – without every parser having to pass ``(output, line)`` tuples.

    Parsers can optionally call ``data.mark_record_start()`` to explicitly mark
    record boundaries for multi-line records.  Otherwise the range is
    automatically tracked from the previous yield to the current yield.
    """

    __slots__ = ('_data', '_line_no', '_record_start_line', '_buffer', '_exhausted', '_offset')

    def __init__(self, data: Iterable[str]) -> None:
        self._data = iter(data)
        # Detect offset from _SlicedIterable (from jc.utils.line_slice)
        self._offset: int = getattr(data, '_jc_line_offset', 0)
        self._line_no: int = self._offset
        self._record_start_line: int = self._offset
        self._buffer: list[str] = []
        self._exhausted: bool = False

    def __iter__(self):
        return self

    def __next__(self) -> str:
        try:
            line = next(self._data)
        except StopIteration:
            self._exhausted = True
            raise
        self._line_no += 1
        self._buffer.append(line)
        return line

    def mark_record_start(self) -> None:
        """Explicitly mark the current line as the start of a new record.

        Call this before consuming the first line of a multi-line record so
        so the next yielded output will have the correct line range.
        """
        self._record_start_line = self._line_no
        self._buffer.clear()

    def get_record_range(self) -> dict:
        """Return the range metadata for the current record.

        Returns a dict with:
        - ``line_start``: first line number of the record (0-indexed)
        - ``line_end``: last line number of the record (0-indexed, inclusive)
        - ``line_count``: number of lines in the record
        - ``line``: first line of the record (stripped), for single-line records
        - ``lines``: all lines of the record (stripped, joined by newlines),
          only present if >1 line
        """
        end_line = self._line_no - 1
        count = end_line - self._record_start_line
        result: JSONDictType = {
            'line_start': self._record_start_line,
            'line_end': end_line,
            'line_count': count + 1 if count >= 0 else 0,
        }
        if self._buffer:
            result['line'] = self._buffer[0].strip()
            if len(self._buffer) > 1:
                result['lines'] = '\n'.join(l.strip() for l in self._buffer)
        return result

    def reset_record(self) -> None:
        """Reset the record buffer after yielding an output is emitted."""
        self._record_start_line = self._line_no
        self._buffer.clear()


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
    range_info: Optional[dict] = None
) -> JSONDictType:
    """Return a new dict with ``_jc_meta`` added when *ignore_exceptions* is
    ``True``.  The original *output_line* is never mutated.

    When *range_info* is provided it is merged into ``_jc_meta`` so that
    every output record – success or failure – carries the original input
    source range when ``ignore_exceptions=True``.

    Parameters
    ----------
    range_info :  dict | None
        Dictionary from ``_LineTracker.get_record_range()`` with keys like
        ``line_start``, ``line_end``, ``line_count``, ``line``, and
        optionally ``lines``.
    """
    result = dict(output_line)
    if ignore_exceptions:
        existing_meta = result.get('_jc_meta', {})
        success_meta: JSONDictType = {'success': True}
        if range_info is not None:
            success_meta.update(range_info)
        success_meta.update(existing_meta)
        result['_jc_meta'] = success_meta
    return result


def stream_error(e: BaseException, line: str) -> JSONDictType:
    """
    Return an error ``_jc_meta`` field.

    The *line* parameter is the input text that caused the error (stripped).
    """
    return {
        '_jc_meta':
            {
                'success': False,
                'error': f'{e.__class__.__name__}: {e}',
                'line': line.strip(),
                'line_count': 1,
            }
    }


def add_jc_meta(func: F) -> F:
    """
    Decorator for streaming parsers that adds ``_jc_meta`` to every yielded
    record when ``ignore_exceptions=True`` (the ``-qq`` CLI option).

    The decorator **automatically tracks the input line range** by wrapping
    the parser's ``data`` parameter in a :class:`_LineTracker`.  Parsers
    should simply ``yield output_dict`` for success and
    ``yield raise_or_yield(…)`` for errors – **no manual tuple
    construction**.

    For multi-line records, parsers can optionally call
    ``data.mark_record_start()`` before consuming the first line of a record
    to ensure the line range is accurate.  Without explicit marking, the
    range is auto-tracked from the previous yield to the current yield.

    With the decorator on parse():

        # successfully parsed line – just yield the dict:
        yield output_line if raw else _process(output_line)

        # unsuccessfully parsed line:
        except Exception as e:
            yield raise_or_yield(ignore_exceptions, e, line)

    Parameters
    ----------

    output_line :  Dict   successfully parsed line yielded as a dict

    e :  BaseException   exception object (first element of the error tuple)

    line :  str   string of the original input line

    ignore_exceptions :  bool   continue processing lines and ignore
                         exceptions if ``True``
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        ignore_exceptions = bound.arguments.get('ignore_exceptions', False)

        tracker: Optional[_LineTracker] = None
        data_arg = bound.arguments.get('data')
        if data_arg is not None:
            tracker = _LineTracker(data_arg)
            bound.arguments['data'] = tracker

        gen = func(*bound.args, **bound.kwargs)
        for value in gen:
            if isinstance(value, dict):
                range_info = tracker.get_record_range() if tracker else None
                yield stream_success(value, ignore_exceptions, range_info)
                if tracker:
                    tracker.reset_record()

            elif isinstance(value, tuple) and len(value) == 2:
                first, second = value
                if isinstance(first, BaseException):
                    yield stream_error(first, second)
                else:
                    yield stream_error(first, second)
                if tracker:
                    tracker.reset_record()

            else:
                exception_obj = value[0]
                line = value[1]
                yield stream_error(exception_obj, line)
                if tracker:
                    tracker.reset_record()

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
    ignore_exceptions_msg = '... Use the ignore_exceptions option (-qq) to ignore streaming parser errors.'

    if not ignore_exceptions:
        e.args = (str(e) + ignore_exceptions_msg,)
        raise e

    return e, line
