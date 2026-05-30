"""jc - JSON Convert streaming utils"""

from functools import wraps
from typing import Tuple, Union, Iterable, Callable, TypeVar, cast, Any, List
from .jc_types import JSONDictType


F = TypeVar('F', bound=Callable[..., Any])

_JC_META_PROGRESS_SCHEMA = r"""
      "_jc_meta": {
        "success":          boolean,     # false if error parsing
        "line_start":       integer,     # 0-based index of first input line
        "line_end":         integer,     # 0-based index of last input line + 1
        "line_count":       integer,     # number of lines consumed (= line_end - line_start)
        "lines_processed":  integer,     # cumulative lines consumed so far
        "error":            string,      # only if "success" is false
        "error_context":    string       # only if "success" is false
      }
"""


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


def _build_meta(
    success: bool,
    line_start: int,
    line_end: int,
    lines_processed: int,
    error: str = '',
    error_context: str = '',
    include_error: bool = False,
    include_context: bool = False
) -> JSONDictType:
    """
    Build the _jc_meta dictionary with consistent field structure.

    line_start: 0-based index of first input line consumed for this record
    line_end:   0-based index of last input line consumed + 1 (exclusive)
    line_count: number of input lines consumed for this record (= line_end - line_start)
    lines_processed: total input lines consumed so far (cumulative)
    error:      error message (only on failure)
    error_context: original line(s) that caused the error (only on failure)
    """
    meta: JSONDictType = {
        'success': success,
        'line_start': line_start,
        'line_end': line_end,
        'line_count': line_end - line_start,
        'lines_processed': lines_processed
    }

    if include_error and error:
        meta['error'] = error

    if include_context and error_context:
        meta['error_context'] = error_context

    return meta


def stream_success(
    output_line: JSONDictType,
    ignore_exceptions: bool,
    line_start: int = 0,
    line_end: int = 0,
    lines_processed: int = 0,
    progress: bool = False
) -> JSONDictType:
    """
    Add `_jc_meta` object to output line if `ignore_exceptions=True` or
    `progress=True`.

    When `progress=True`, the `_jc_meta` object includes line range and
    cumulative line count.
    """
    if ignore_exceptions or progress:
        output_line['_jc_meta'] = _build_meta(
            success=True,
            line_start=line_start,
            line_end=line_end,
            lines_processed=lines_processed
        )

    return output_line


def stream_error(
    e: BaseException,
    line: str,
    line_start: int = 0,
    line_end: int = 0,
    lines_processed: int = 0,
    progress: bool = False
) -> JSONDictType:
    """
    Return an error `_jc_meta` field.

    When `progress=True`, also includes line range and cumulative line count.
    Always includes error message and context when -qq is used.
    """
    error_msg = f'{e.__class__.__name__}: {e}'
    return {
        '_jc_meta': _build_meta(
            success=False,
            line_start=line_start,
            line_end=line_end,
            lines_processed=lines_processed,
            error=error_msg,
            error_context=line.strip(),
            include_error=True,
            include_context=True
        )
    }


def add_jc_meta(func: F) -> F:
    """
    Decorator for streaming parsers to add `stream_success` and
    `stream_error` objects. This simplifies the `yield` lines in the
    streaming parsers.

    When `progress=True` is passed, the decorator wraps the input data
    iterable to track each consumed line with its 0-based index. Between
    yields, it records all lines consumed since the last yield to compute
    `line_start`, `line_end`, and `line_count` for each output record.
    This works for both single-line and multi-line parsers.

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

        progress:     (bool)  add progress metadata (line_start/line_end/
                      line_count/lines_processed) to `_jc_meta` if `True`.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        progress = kwargs.pop('progress', False)
        ignore_exceptions = kwargs.get('ignore_exceptions', False)

        lines_processed = 0

        if progress:
            original_data = args[0]
            last_yield_line = 0

            def _tracking_iter(data):
                nonlocal lines_processed
                for item in data:
                    lines_processed += 1
                    yield item

            args = (_tracking_iter(original_data),) + args[1:]

            gen = func(*args, **kwargs)
            for value in gen:
                if isinstance(value, dict):
                    current_line_end = lines_processed
                    yield stream_success(
                        value,
                        ignore_exceptions,
                        line_start=last_yield_line,
                        line_end=current_line_end,
                        lines_processed=current_line_end,
                        progress=progress
                    )
                    last_yield_line = current_line_end

                else:
                    exception_obj = value[0]
                    line = value[1]
                    current_line_end = lines_processed
                    yield stream_error(
                        exception_obj,
                        line,
                        line_start=last_yield_line,
                        line_end=current_line_end,
                        lines_processed=current_line_end,
                        progress=progress
                    )
                    last_yield_line = current_line_end

        else:
            gen = func(*args, **kwargs)
            for value in gen:
                if isinstance(value, dict):
                    yield stream_success(value, ignore_exceptions)
                else:
                    exception_obj = value[0]
                    line = value[1]
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
    ignore_exceptions_msg = '... Use the ignore_exceptions option (-qq) to ignore streaming parser errors.'

    if not ignore_exceptions:
        e.args = (str(e) + ignore_exceptions_msg,)
        raise e

    return e, line
