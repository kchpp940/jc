import unittest
import os
import ast
import glob
import jc.streaming
from jc.streaming import StreamingContext, streaming_parser

_PARSERS_DIR = os.path.join(os.path.dirname(__file__), '..', 'jc', 'parsers')


class MyTests(unittest.TestCase):

    # ── Legacy helpers (backward compat) ────────────────────────────

    def test_streaming_input_type_check_wrong(self):
        self.assertRaises(TypeError, jc.streaming.streaming_input_type_check, 'abc')

    def test_streaming_input_type_check_correct(self):
        self.assertEqual(jc.streaming.streaming_input_type_check(['abc']), None)

    def test_streaming_line_input_type_check_wrong(self):
        self.assertRaises(TypeError, jc.streaming.streaming_line_input_type_check, ['abc'])

    def test_streaming_line_input_type_check_correct(self):
        self.assertEqual(jc.streaming.streaming_line_input_type_check('abc'), None)

    def test_stream_success_ignore_exceptions_true(self):
        self.assertEqual(jc.streaming.stream_success({}, True), {'_jc_meta': {'success': True}})

    def test_stream_success_ignore_exceptions_false(self):
        self.assertEqual(jc.streaming.stream_success({}, False), {})

    def test_stream_error(self):
        self.assertEqual(jc.streaming.stream_error(
            TypeError, 'this is a test'),
            {
                '_jc_meta':
                    {
                        'success': False,
                        'error': 'type: <class \'TypeError\'>',
                        'line': 'this is a test'
                    }
            }
        )

    def test_raise_or_yield_ignore_exceptions(self):
        self.assertEqual(jc.streaming.raise_or_yield(
            True, TypeError, 'this is a test'),
            (TypeError, 'this is a test')
        )

    def test_raise_or_yield_ignore_exceptions_false(self):
        self.assertRaises(
            TypeError,
            jc.streaming.raise_or_yield,
            False, TypeError, 'this is a test'
        )

    # ── stream_success with line_number / progress ──────────────────

    def test_stream_success_with_line_number(self):
        result = jc.streaming.stream_success({'key': 'val'}, True, line_number=5)
        self.assertEqual(result, {
            'key': 'val',
            '_jc_meta': {'success': True, 'line_number': 5}
        })

    def test_stream_success_with_progress(self):
        result = jc.streaming.stream_success({'key': 'val'}, True, progress={'line_number': 3, 'item_count': 1})
        self.assertEqual(result, {
            'key': 'val',
            '_jc_meta': {'success': True, 'progress': {'line_number': 3, 'item_count': 1}}
        })

    def test_stream_success_without_meta_when_not_ignoring(self):
        result = jc.streaming.stream_success({'key': 'val'}, False, line_number=5)
        self.assertEqual(result, {'key': 'val'})

    def test_stream_error_with_line_number(self):
        result = jc.streaming.stream_error(ValueError('bad'), 'line text', line_number=7)
        self.assertEqual(result['_jc_meta']['line_number'], 7)
        self.assertEqual(result['_jc_meta']['success'], False)

    def test_stream_error_with_progress(self):
        result = jc.streaming.stream_error(ValueError('bad'), 'line text', progress={'line_number': 7, 'item_count': 2})
        self.assertEqual(result['_jc_meta']['progress'], {'line_number': 7, 'item_count': 2})

    # ── StreamingContext ─────────────────────────────────────────────

    def test_ctx_check_line_increments(self):
        ctx = StreamingContext()
        self.assertEqual(ctx.line_number, 0)
        ctx.check_line('line1')
        self.assertEqual(ctx.line_number, 1)
        ctx.check_line('line2')
        self.assertEqual(ctx.line_number, 2)

    def test_ctx_check_line_type_error(self):
        ctx = StreamingContext()
        self.assertRaises(TypeError, ctx.check_line, 123)

    def test_ctx_emit_raw_mode(self):
        ctx = StreamingContext(raw=True)
        result = ctx.emit({'key': 'val'})
        self.assertEqual(result, {'key': 'val'})
        self.assertEqual(ctx.item_count, 1)

    def test_ctx_emit_with_process_fn(self):
        ctx = StreamingContext(raw=False)
        result = ctx.emit({'num': '42'}, lambda d: {**d, 'num': int(d['num'])})
        self.assertEqual(result, {'num': 42})
        self.assertEqual(ctx.item_count, 1)

    def test_ctx_emit_increments_item_count(self):
        ctx = StreamingContext(raw=True)
        ctx.emit({})
        ctx.emit({})
        ctx.emit({})
        self.assertEqual(ctx.item_count, 3)

    def test_ctx_handle_exception_raises(self):
        ctx = StreamingContext(ignore_exceptions=False)
        with self.assertRaises(ValueError):
            ctx.handle_exception(ValueError('bad'), 'line')

    def test_ctx_handle_exception_returns_tuple(self):
        ctx = StreamingContext(ignore_exceptions=True)
        exc = ValueError('bad')
        result = ctx.handle_exception(exc, 'line')
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertIs(result[0], exc)
        self.assertEqual(result[1], 'line')

    def test_ctx_record_success_no_tracking(self):
        ctx = StreamingContext(ignore_exceptions=True)
        result = ctx.record_success({'key': 'val'})
        self.assertEqual(result, {'key': 'val', '_jc_meta': {'success': True}})

    def test_ctx_record_success_with_line_number(self):
        ctx = StreamingContext(ignore_exceptions=True, track_line_number=True)
        ctx.check_line('line1')
        result = ctx.record_success({'key': 'val'})
        self.assertEqual(result['_jc_meta']['line_number'], 1)

    def test_ctx_record_success_no_meta_when_not_ignoring(self):
        ctx = StreamingContext(ignore_exceptions=False)
        result = ctx.record_success({'key': 'val'})
        self.assertNotIn('_jc_meta', result)

    def test_ctx_record_error(self):
        ctx = StreamingContext(ignore_exceptions=True)
        result = ctx.record_error(ValueError('bad'), 'line text')
        self.assertEqual(result['_jc_meta']['success'], False)
        self.assertIn('error', result['_jc_meta'])
        self.assertEqual(result['_jc_meta']['line'], 'line text')

    def test_ctx_record_error_with_line_number(self):
        ctx = StreamingContext(track_line_number=True)
        ctx.check_line('line1')
        ctx.check_line('line2')
        result = ctx.record_error(ValueError('bad'), 'line2')
        self.assertEqual(result['_jc_meta']['line_number'], 2)

    def test_ctx_progress_not_tracking(self):
        ctx = StreamingContext()
        self.assertIsNone(ctx.progress)

    def test_ctx_progress_tracking(self):
        ctx = StreamingContext(track_progress=True)
        ctx.check_line('line1')
        ctx.emit({'k': 'v'}, lambda d: d)
        self.assertEqual(ctx.progress, {'line_number': 1, 'item_count': 1})

    def test_ctx_progress_in_meta(self):
        ctx = StreamingContext(ignore_exceptions=True, track_progress=True)
        ctx.check_line('line1')
        ctx.emit({'k': 'v'})
        result = ctx.record_success({'k': 'v'})
        self.assertIn('progress', result['_jc_meta'])
        self.assertEqual(result['_jc_meta']['progress']['item_count'], 1)

    # ── @streaming_parser decorator ──────────────────────────────────

    def test_streaming_parser_basic(self):
        @streaming_parser
        def my_parse(data, raw=False, quiet=False, ignore_exceptions=False, ctx=None):
            for line in data:
                try:
                    ctx.check_line(line)
                    yield ctx.emit({'line': line})
                except Exception as e:
                    yield ctx.handle_exception(e, line)

        result = list(my_parse(['hello', 'world'], ignore_exceptions=True))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['line'], 'hello')
        self.assertIn('_jc_meta', result[0])
        self.assertTrue(result[0]['_jc_meta']['success'])

    def test_streaming_parser_error_handling(self):
        @streaming_parser
        def my_parse(data, raw=False, quiet=False, ignore_exceptions=False, ctx=None):
            for line in data:
                try:
                    ctx.check_line(line)
                    raise ValueError('test error')
                except Exception as e:
                    yield ctx.handle_exception(e, line)

        result = list(my_parse(['hello'], ignore_exceptions=True))
        self.assertEqual(len(result), 1)
        self.assertFalse(result[0]['_jc_meta']['success'])
        self.assertIn('ValueError', result[0]['_jc_meta']['error'])

    def test_streaming_parser_raises_without_ignore(self):
        @streaming_parser
        def my_parse(data, raw=False, quiet=False, ignore_exceptions=False, ctx=None):
            for line in data:
                try:
                    ctx.check_line(line)
                    raise ValueError('test error')
                except Exception as e:
                    yield ctx.handle_exception(e, line)

        with self.assertRaises(ValueError):
            list(my_parse(['hello'], ignore_exceptions=False))

    def test_streaming_parser_input_type_check(self):
        @streaming_parser
        def my_parse(data, raw=False, quiet=False, ignore_exceptions=False, ctx=None):
            for line in data:
                yield ctx.emit({'line': line})

        with self.assertRaises(TypeError):
            list(my_parse('not an iterable of lines'))

    def test_streaming_parser_with_process_fn(self):
        @streaming_parser
        def my_parse(data, raw=False, quiet=False, ignore_exceptions=False, ctx=None):
            for line in data:
                try:
                    ctx.check_line(line)
                    yield ctx.emit({'val': line}, lambda d: {**d, 'val': int(d['val'])})
                except Exception as e:
                    yield ctx.handle_exception(e, line)

        result = list(my_parse(['42', '99'], raw=False, ignore_exceptions=True))
        self.assertEqual(result[0]['val'], 42)
        self.assertEqual(result[1]['val'], 99)

    def test_streaming_parser_raw_mode(self):
        @streaming_parser
        def my_parse(data, raw=False, quiet=False, ignore_exceptions=False, ctx=None):
            for line in data:
                try:
                    ctx.check_line(line)
                    yield ctx.emit({'val': line}, lambda d: {**d, 'val': int(d['val'])})
                except Exception as e:
                    yield ctx.handle_exception(e, line)

        result = list(my_parse(['42'], raw=True, ignore_exceptions=True))
        self.assertEqual(result[0]['val'], '42')

    def test_streaming_parser_with_line_number_tracking(self):
        @streaming_parser
        def my_parse(data, raw=False, quiet=False, ignore_exceptions=False, ctx=None):
            for line in data:
                try:
                    ctx.check_line(line)
                    yield ctx.emit({'line': line})
                except Exception as e:
                    yield ctx.handle_exception(e, line)

        result = list(my_parse(['a', 'b', 'c'], ignore_exceptions=True, track_line_number=True))
        self.assertEqual(result[0]['_jc_meta']['line_number'], 1)
        self.assertEqual(result[1]['_jc_meta']['line_number'], 2)
        self.assertEqual(result[2]['_jc_meta']['line_number'], 3)

    def test_streaming_parser_with_progress_tracking(self):
        @streaming_parser
        def my_parse(data, raw=False, quiet=False, ignore_exceptions=False, ctx=None):
            for line in data:
                try:
                    ctx.check_line(line)
                    yield ctx.emit({'line': line})
                except Exception as e:
                    yield ctx.handle_exception(e, line)

        result = list(my_parse(['a', 'b'], ignore_exceptions=True, track_progress=True))
        self.assertIn('progress', result[0]['_jc_meta'])
        self.assertIn('progress', result[1]['_jc_meta'])

    # ── add_jc_meta backward compat ─────────────────────────────────

    def test_add_jc_meta_backward_compat(self):
        @jc.streaming.add_jc_meta
        def my_parse(data, raw=False, quiet=False, ignore_exceptions=False):
            for line in data:
                try:
                    jc.streaming.streaming_line_input_type_check(line)
                    yield {'line': line} if raw else {'line': line.upper()}
                except Exception as e:
                    yield jc.streaming.raise_or_yield(ignore_exceptions, e, line)

        result = list(my_parse(['hello'], ignore_exceptions=True))
        self.assertIn('_jc_meta', result[0])
        self.assertTrue(result[0]['_jc_meta']['success'])

    # ── Migration consistency checks ────────────────────────────────

    def _all_streaming_parsers(self):
        """Return list of paths for all *_s.py that are true streaming parsers."""
        result = []
        for path in sorted(glob.glob(os.path.join(_PARSERS_DIR, '*_s.py'))):
            basename = os.path.basename(path)
            if basename == 'airport_s.py':
                continue
            result.append(path)
        return result

    def test_no_old_api_imports_in_streaming_parsers(self):
        OLD_APIS = ['add_jc_meta', 'raise_or_yield',
                     'streaming_input_type_check', 'streaming_line_input_type_check']
        violations = {}
        for path in self._all_streaming_parsers():
            name = os.path.basename(path)
            source = open(path, encoding='utf-8').read()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id in OLD_APIS:
                    violations.setdefault(name, set()).add(node.id)
                if isinstance(node, ast.Attribute) and node.attr in OLD_APIS:
                    violations.setdefault(name, set()).add(node.attr)
                if isinstance(node, ast.alias) and node.name in OLD_APIS:
                    violations.setdefault(name, set()).add(node.name)
        self.assertEqual(
            violations, {},
            f'Streaming parsers still reference old APIs: {violations}'
        )

    def test_all_streaming_parsers_use_streaming_parser_decorator(self):
        missing = []
        for path in self._all_streaming_parsers():
            name = os.path.basename(path)
            source = open(path, encoding='utf-8').read()
            tree = ast.parse(source)
            has_decorator = False
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == 'parse':
                    for dec in node.decorator_list:
                        if isinstance(dec, ast.Name) and dec.id == 'streaming_parser':
                            has_decorator = True
                        elif isinstance(dec, ast.Attribute) and dec.attr == 'streaming_parser':
                            has_decorator = True
            if not has_decorator:
                missing.append(name)
        self.assertEqual(
            missing, [],
            f'Streaming parsers missing @streaming_parser: {missing}'
        )

    def test_all_streaming_parsers_import_streaming_context(self):
        missing = []
        for path in self._all_streaming_parsers():
            name = os.path.basename(path)
            source = open(path, encoding='utf-8').read()
            if 'StreamingContext' not in source:
                missing.append(name)
        self.assertEqual(
            missing, [],
            f'Streaming parsers missing StreamingContext import: {missing}'
        )

    def test_all_streaming_parsers_have_ctx_emit(self):
        missing = []
        for path in self._all_streaming_parsers():
            name = os.path.basename(path)
            source = open(path, encoding='utf-8').read()
            if 'ctx.emit' not in source:
                missing.append(name)
        self.assertEqual(
            missing, [],
            f'Streaming parsers missing ctx.emit: {missing}'
        )

    def test_all_streaming_parsers_have_ctx_handle_exception(self):
        missing = []
        for path in self._all_streaming_parsers():
            name = os.path.basename(path)
            source = open(path, encoding='utf-8').read()
            if 'ctx.handle_exception' not in source:
                missing.append(name)
        self.assertEqual(
            missing, [],
            f'Streaming parsers missing ctx.handle_exception: {missing}'
        )

    def test_complex_parsers_have_multiple_emit_paths(self):
        COMPLEX_PARSERS = {
            'git_log_s.py': 2,
            'top_s.py': 2,
            'stat_s.py': 2,
            'pidstat_s.py': 2,
            'traceroute_s.py': 2,
            'rsync_s.py': 3,
        }
        violations = []
        for path in self._all_streaming_parsers():
            name = os.path.basename(path)
            if name not in COMPLEX_PARSERS:
                continue
            source = open(path, encoding='utf-8').read()
            count = source.count('ctx.emit')
            expected = COMPLEX_PARSERS[name]
            if count < expected:
                violations.append(f'{name}: found {count} ctx.emit calls, expected >= {expected}')
        self.assertEqual(
            violations, [],
            f'Complex parser emit path violations: {violations}'
        )

    def test_no_yield_raw_process_pattern(self):
        violations = []
        for path in self._all_streaming_parsers():
            name = os.path.basename(path)
            source = open(path, encoding='utf-8').read()
            if ' if raw else _process(' in source:
                violations.append(name)
        self.assertEqual(
            violations, [],
            f'Streaming parsers still use "yield x if raw else _process(x)" pattern: {violations}'
        )


if __name__ == '__main__':
    unittest.main()
