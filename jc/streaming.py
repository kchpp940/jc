"""jc - JSON Convert streaming utils"""

from functools import wraps
from typing import Tuple, Union, Iterable, Callable, TypeVar, cast, Any, Optional, Dict, List
from .jc_types import JSONDictType
from . import utils


F = TypeVar('F', bound=Callable[..., Any])
G = TypeVar('G', bound=Callable[..., Any])
ParserState = Dict[str, Any]
ParseLineResult = Optional[Union[JSONDictType, List[JSONDictType]]]


def streaming_input_type_check(data: Iterable[Union[str, bytes]]) -> None:
    """Internal: ensure input is a non-string iterable."""
    if not hasattr(data, '__iter__') or isinstance(data, (str, bytes)):
        raise TypeError("Input data must be a non-string iterable object.")


def streaming_line_input_type_check(line: str) -> None:
    """Internal: ensure each line is a string."""
    if not isinstance(line, str):
        raise TypeError("Input line must be a 'str' object.")


def stream_success(output_line: JSONDictType, ignore_exceptions: bool) -> JSONDictType:
    """Internal: add `_jc_meta.success` when ignore_exceptions=True."""
    if ignore_exceptions:
        output_line.update({'_jc_meta': {'success': True}})
    return output_line


def stream_error(e: BaseException, line: str) -> JSONDictType:
    """Internal: construct an error `_jc_meta` field."""
    return {
        '_jc_meta':
            {
                'success': False,
                'error': f'{e.__class__.__name__}: {e}',
                'line': line.strip()
            }
    }


def add_jc_meta(func: F) -> F:
    """Internal: decorator that wires up _jc_meta on success/error."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        ignore_exceptions = kwargs.get('ignore_exceptions', False)
        gen = func(*args, **kwargs)
        for value in gen:
            if isinstance(value, dict):
                yield stream_success(value, ignore_exceptions)
            else:
                exception_obj, line = value
                yield stream_error(exception_obj, line)
    return cast(F, wrapper)


def raise_or_yield(
    ignore_exceptions: bool,
    e: BaseException,
    line: str
) -> Tuple[BaseException, str]:
    """Internal: either re-raise or return (exception, line) tuple."""
    if not ignore_exceptions:
        e.args = (str(e) + '... Use the ignore_exceptions option (-qq) to ignore streaming parser errors.',)
        raise e
    return e, line


def _yield_result(result, raw, process_func, state, quiet):
    if result is None:
        return
    if isinstance(result, list):
        for item in result:
            if item is not None:
                if raw or process_func is None:
                    yield item
                else:
                    yield process_func(item, **_process_kwargs(process_func, state, quiet))
    else:
        if raw or process_func is None:
            yield result
        else:
            yield process_func(result, **_process_kwargs(process_func, state, quiet))


def _process_kwargs(func, state, quiet):
    import inspect
    sig = inspect.signature(func)
    kw = {}
    if 'quiet' in sig.parameters:
        kw['quiet'] = quiet
    if 'idx' in sig.parameters:
        kw['idx'] = state.get('idx', 0)
    return kw


def streaming_parser(
    info_cls: Any,
    process_func: Optional[Callable[..., JSONDictType]] = None,
    init_state: Optional[Callable[[], ParserState]] = None,
    has_final_yield: bool = False,
    preprocess: Optional[Callable[[Iterable[str], ParserState], Iterable[Any]]] = None
) -> Callable[[G], Callable[..., Any]]:
    """
    Unified decorator for all streaming parsers.

    Encapsulates common logic: compatibility check, input type check,
    line iteration, exception handling, and _jc_meta enrichment.

    The decorated function only needs to implement per-item parsing logic.
    It should always return raw data - the decorator handles the raw/process
    decision. parse_line must NEVER call _process itself.

    parse_line signature:

        def parse_line(
            line: str,           # current item (string line, or None for final yield)
            state: ParserState,  # mutable state dict
            raw: bool,           # if True, skip process_func
            quiet: bool          # suppress warnings
        ) -> ParseLineResult:
            # return Dict:   yield this item (raw - decorator handles process)
            # return None:   skip (accumulate state)
            # return [Dict]: yield multiple items from one line

    Parameters:
        info_cls:        parser info class (compatible, etc.)
        process_func:    post-processing function (e.g. _process). Always
                         receives the raw dict. If the function accepts a
                         `quiet` keyword argument, it will be passed.
        init_state:      state initializer callable. Returns initial state dict.
        has_final_yield: if True, calls parse_line(None, state, raw, quiet)
                         after the loop for final accumulated output.
        preprocess:      optional callable(data, state) -> iterable. Transforms
                         the input data before iteration. When set,
                         streaming_line_input_type_check is skipped for items.

    Examples:

        # Stateful parser with final yield:
        @streaming_parser(info, _process, _init_state, has_final_yield=True)
        def parse(line, state, raw, quiet):
            ...

        # Simple stateless parser:
        @streaming_parser(info, _process)
        def parse(line, state, raw, quiet):
            ...

        # Custom iteration (e.g. csv DictReader):
        def _preprocess(data, state):
            reader = csv.DictReader(data, dialect=state['dialect'])
            return reader

        @streaming_parser(info, _process, preprocess=_preprocess)
        def parse(row, state, raw, quiet):
            return dict(row)

        # Parser whose _process needs extra context (idx, quiet):
        # Store idx in state; _process receives quiet automatically.
        @streaming_parser(info, _process, _init_state)
        def parse(line, state, raw, quiet):
            state['idx'] += 1
            return raw_output
    """
    def decorator(parse_line_func: G) -> Callable[..., Any]:
        @add_jc_meta
        @wraps(parse_line_func)
        def wrapper(
            data: Iterable[str],
            raw: bool = False,
            quiet: bool = False,
            ignore_exceptions: bool = False
        ) -> Any:
            utils.compatibility(parse_line_func.__module__, info_cls.compatible, quiet)
            streaming_input_type_check(data)

            state: ParserState = init_state() if init_state else {}
            iter_data = preprocess(data, state) if preprocess else data

            for item in iter_data:
                try:
                    if preprocess is None:
                        streaming_line_input_type_check(item)
                    result = parse_line_func(item, state, raw, quiet)
                    yield from _yield_result(result, raw, process_func, state, quiet)
                except Exception as e:
                    yield raise_or_yield(ignore_exceptions, e, str(item))

            if has_final_yield:
                try:
                    result = parse_line_func(None, state, raw, quiet)
                    yield from _yield_result(result, raw, process_func, state, quiet)
                except Exception as e:
                    yield raise_or_yield(ignore_exceptions, e, '')

        return cast(Callable[..., Any], wrapper)

    return decorator
