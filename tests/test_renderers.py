"""Tests for the unified renderer/formatter pipeline.

Validates that all output paths — standard, streaming, --meta-out, -qq errors,
JSON, YAML, NDJSON — flow through the same renderer interfaces and that no
code path manually constructs _jc_meta outside of injector/wrapper classes.
"""

import json
import unittest
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from jc.renderers import (
    RenderingContext,
    OutputFormatter,
    MetaInjector,
    ErrorWrapper,
    JsonFormatter,
    YamlFormatter,
    NdjsonFormatter,
    NoopMetaInjector,
    MetaOutInjector,
    StreamingMetaInjector,
    StreamingErrorWrapper,
    OutputRenderer,
    create_renderer,
)
from jc.streaming import stream_success, stream_error, add_jc_meta


def _ctx(
    parser_name: Optional[str] = 'test-parser',
    run_timestamp: Optional[datetime] = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    **overrides: Any,
) -> RenderingContext:
    defaults: Dict[str, Any] = {
        'parser_name': parser_name,
        'run_timestamp': run_timestamp,
        'mono': True,
    }
    defaults.update(overrides)
    return RenderingContext(**defaults)


class TestJsonFormatter(unittest.TestCase):

    def test_format_dict(self):
        ctx = _ctx()
        result = JsonFormatter().format({'a': 1}, ctx)
        self.assertEqual(json.loads(result), {'a': 1})

    def test_format_list(self):
        ctx = _ctx()
        result = JsonFormatter().format([{'a': 1}, {'b': 2}], ctx)
        self.assertEqual(json.loads(result), [{'a': 1}, {'b': 2}])

    def test_format_pretty(self):
        ctx = _ctx(pretty=True)
        result = JsonFormatter().format({'a': 1}, ctx)
        self.assertIn('\n', result)
        self.assertEqual(json.loads(result), {'a': 1})

    def test_format_ascii_only(self):
        ctx = _ctx(ascii_only=True)
        result = JsonFormatter().format({'k': '日本語'}, ctx)
        self.assertNotIn('日本語', result)

    def test_format_streaming_compact(self):
        ctx = _ctx()
        result = JsonFormatter().format_streaming({'a': 1}, ctx)
        self.assertNotIn('\n', result)
        self.assertEqual(json.loads(result), {'a': 1})

    def test_non_serializable_fallback_to_str(self):
        ctx = _ctx()
        result = JsonFormatter().format({'obj': object()}, ctx)
        parsed = json.loads(result)
        self.assertIn('obj', parsed)


class TestNdjsonFormatter(unittest.TestCase):

    def test_format_streaming_single(self):
        ctx = _ctx()
        result = NdjsonFormatter().format_streaming({'a': 1}, ctx)
        self.assertEqual(json.loads(result), {'a': 1})

    def test_format_list_as_ndjson(self):
        ctx = _ctx()
        result = NdjsonFormatter().format([{'a': 1}, {'b': 2}], ctx)
        lines = result.strip().split('\n')
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0]), {'a': 1})
        self.assertEqual(json.loads(lines[1]), {'b': 2})

    def test_format_single_dict(self):
        ctx = _ctx()
        result = NdjsonFormatter().format({'a': 1}, ctx)
        self.assertEqual(json.loads(result), {'a': 1})


class TestNoopMetaInjector(unittest.TestCase):

    def test_no_injection(self):
        ctx = _ctx()
        data = {'a': 1}
        result = NoopMetaInjector().inject(data, ctx)
        self.assertNotIn('_jc_meta', result)
        self.assertEqual(result, {'a': 1})

    def test_list_no_injection(self):
        ctx = _ctx()
        data = [{'a': 1}]
        result = NoopMetaInjector().inject(data, ctx)
        self.assertNotIn('_jc_meta', result[0])


class TestMetaOutInjector(unittest.TestCase):

    def test_inject_into_dict(self):
        ctx = _ctx()
        result = MetaOutInjector().inject({'a': 1}, ctx)
        self.assertIn('_jc_meta', result)
        self.assertEqual(result['_jc_meta']['parser'], 'test-parser')
        self.assertIsNotNone(result['_jc_meta']['timestamp'])
        self.assertIsNone(result['_jc_meta']['slice_start'])

    def test_inject_into_list(self):
        ctx = _ctx()
        result = MetaOutInjector().inject([{'a': 1}, {'b': 2}], ctx)
        for item in result:
            self.assertIn('_jc_meta', item)
            self.assertEqual(item['_jc_meta']['parser'], 'test-parser')

    def test_inject_into_empty_list_adds_empty_dict(self):
        ctx = _ctx()
        result = MetaOutInjector().inject([], ctx)
        self.assertEqual(len(result), 1)
        self.assertIn('_jc_meta', result[0])

    def test_inject_with_magic_command(self):
        ctx = _ctx(magic_command=['ls', '-al'], magic_command_exit=0)
        result = MetaOutInjector().inject({'a': 1}, ctx)
        self.assertEqual(result['_jc_meta']['magic_command'], ['ls', '-al'])
        self.assertEqual(result['_jc_meta']['magic_command_exit'], 0)

    def test_inject_with_input_list(self):
        ctx = _ctx(input_list=['file1', 'file2'])
        result = MetaOutInjector().inject({'a': 1}, ctx)
        self.assertEqual(result['_jc_meta']['input_list'], ['file1', 'file2'])

    def test_inject_with_slice(self):
        ctx = _ctx(slice_start=5, slice_end=10)
        result = MetaOutInjector().inject({'a': 1}, ctx)
        self.assertEqual(result['_jc_meta']['slice_start'], 5)
        self.assertEqual(result['_jc_meta']['slice_end'], 10)

    def test_inject_auto_timestamp_when_none(self):
        ctx = _ctx(run_timestamp=None)
        result = MetaOutInjector().inject({'a': 1}, ctx)
        self.assertIsNotNone(ctx.run_timestamp)
        self.assertIsNotNone(result['_jc_meta']['timestamp'])

    def test_inject_preserves_existing_meta(self):
        ctx = _ctx()
        data = {'a': 1, '_jc_meta': {'existing': 'value'}}
        result = MetaOutInjector().inject(data, ctx)
        self.assertEqual(result['_jc_meta']['existing'], 'value')
        self.assertEqual(result['_jc_meta']['parser'], 'test-parser')

    def test_inject_no_meta_when_no_timestamp_and_not_auto_set(self):
        injector = MetaOutInjector()
        ctx = _ctx(run_timestamp=None)
        result = injector.inject({'a': 1}, ctx)
        self.assertIn('_jc_meta', result)
        self.assertIsNotNone(result['_jc_meta']['timestamp'])


class TestStreamingMetaInjector(unittest.TestCase):

    def test_no_injection_when_not_ignore(self):
        ctx = _ctx()
        result = StreamingMetaInjector(ignore_exceptions=False).inject({'a': 1}, ctx)
        self.assertNotIn('_jc_meta', result)

    def test_inject_success_when_ignore(self):
        ctx = _ctx()
        result = StreamingMetaInjector(ignore_exceptions=True).inject({'a': 1}, ctx)
        self.assertIn('_jc_meta', result)
        self.assertTrue(result['_jc_meta']['success'])

    def test_preserves_existing_meta(self):
        ctx = _ctx()
        data = {'a': 1, '_jc_meta': {'existing': True}}
        result = StreamingMetaInjector(ignore_exceptions=True).inject(data, ctx)
        self.assertTrue(result['_jc_meta']['success'])
        self.assertTrue(result['_jc_meta']['existing'])


class TestStreamingErrorWrapper(unittest.TestCase):

    def test_wrap_with_line(self):
        ctx = _ctx()
        result = StreamingErrorWrapper().wrap(ValueError('oops'), 'bad line', ctx)
        self.assertFalse(result['_jc_meta']['success'])
        self.assertIn('ValueError: oops', result['_jc_meta']['error'])
        self.assertEqual(result['_jc_meta']['line'], 'bad line')

    def test_wrap_without_line(self):
        ctx = _ctx()
        result = StreamingErrorWrapper().wrap(RuntimeError('fail'), None, ctx)
        self.assertFalse(result['_jc_meta']['success'])
        self.assertNotIn('line', result['_jc_meta'])

    def test_wrap_strips_line(self):
        ctx = _ctx()
        result = StreamingErrorWrapper().wrap(ValueError('x'), '  spaces  ', ctx)
        self.assertEqual(result['_jc_meta']['line'], 'spaces')


class TestOutputRendererPipeline(unittest.TestCase):

    def test_render_json_no_meta(self):
        renderer = OutputRenderer(JsonFormatter(), NoopMetaInjector())
        ctx = _ctx()
        result = renderer.render({'a': 1}, ctx)
        parsed = json.loads(result)
        self.assertNotIn('_jc_meta', parsed)
        self.assertEqual(parsed['a'], 1)

    def test_render_json_with_meta_out(self):
        renderer = OutputRenderer(JsonFormatter(), MetaOutInjector())
        ctx = _ctx()
        result = renderer.render({'a': 1}, ctx)
        parsed = json.loads(result)
        self.assertIn('_jc_meta', parsed)
        self.assertEqual(parsed['_jc_meta']['parser'], 'test-parser')

    def test_render_streaming_with_success_meta(self):
        renderer = OutputRenderer(
            NdjsonFormatter(),
            StreamingMetaInjector(ignore_exceptions=True),
        )
        ctx = _ctx()
        result = renderer.render_streaming({'a': 1}, ctx)
        parsed = json.loads(result)
        self.assertTrue(parsed['_jc_meta']['success'])

    def test_render_error(self):
        renderer = OutputRenderer(
            NdjsonFormatter(),
            StreamingMetaInjector(ignore_exceptions=True),
            StreamingErrorWrapper(),
        )
        ctx = _ctx()
        result = renderer.render_error(ValueError('bad'), 'input line', ctx)
        parsed = json.loads(result)
        self.assertFalse(parsed['_jc_meta']['success'])
        self.assertIn('ValueError: bad', parsed['_jc_meta']['error'])

    def test_render_error_raises_without_wrapper(self):
        renderer = OutputRenderer(NdjsonFormatter(), NoopMetaInjector())
        ctx = _ctx()
        with self.assertRaises(ValueError):
            renderer.render_error(ValueError('bad'), 'line', ctx)


class TestCreateRenderer(unittest.TestCase):

    def test_default_is_json_noop(self):
        r = create_renderer()
        self.assertIsInstance(r.formatter, JsonFormatter)
        self.assertIsInstance(r.meta_injector, NoopMetaInjector)
        self.assertIsNone(r.error_wrapper)

    def test_yaml_output(self):
        r = create_renderer(yaml_output=True)
        self.assertIsInstance(r.formatter, YamlFormatter)
        self.assertIsInstance(r.meta_injector, NoopMetaInjector)

    def test_meta_out(self):
        r = create_renderer(meta_out=True)
        self.assertIsInstance(r.formatter, JsonFormatter)
        self.assertIsInstance(r.meta_injector, MetaOutInjector)

    def test_streaming(self):
        r = create_renderer(streaming=True)
        self.assertIsInstance(r.formatter, NdjsonFormatter)
        self.assertIsInstance(r.meta_injector, NoopMetaInjector)
        self.assertIsNone(r.error_wrapper)

    def test_streaming_with_qq(self):
        r = create_renderer(streaming=True, ignore_exceptions=True)
        self.assertIsInstance(r.formatter, NdjsonFormatter)
        self.assertIsInstance(r.meta_injector, StreamingMetaInjector)
        self.assertIsInstance(r.error_wrapper, StreamingErrorWrapper)

    def test_streaming_with_meta_out(self):
        r = create_renderer(streaming=True, meta_out=True)
        self.assertIsInstance(r.formatter, NdjsonFormatter)
        self.assertIsInstance(r.meta_injector, MetaOutInjector)

    def test_yaml_with_meta_out(self):
        r = create_renderer(yaml_output=True, meta_out=True)
        self.assertIsInstance(r.formatter, YamlFormatter)
        self.assertIsInstance(r.meta_injector, MetaOutInjector)

    def test_ignore_exceptions_without_streaming_is_noop(self):
        r = create_renderer(ignore_exceptions=True)
        self.assertIsInstance(r.meta_injector, NoopMetaInjector)
        self.assertIsNone(r.error_wrapper)


class TestStreamingAdapterDelegation(unittest.TestCase):

    def test_stream_success_true_delegates_to_injector(self):
        result = stream_success({'a': 1}, True)
        self.assertIn('_jc_meta', result)
        self.assertTrue(result['_jc_meta']['success'])

    def test_stream_success_false_delegates_to_injector(self):
        result = stream_success({'a': 1}, False)
        self.assertNotIn('_jc_meta', result)

    def test_stream_error_delegates_to_wrapper(self):
        result = stream_error(ValueError('x'), 'line')
        self.assertFalse(result['_jc_meta']['success'])
        self.assertIn('ValueError: x', result['_jc_meta']['error'])
        self.assertEqual(result['_jc_meta']['line'], 'line')


class TestAddJcMetaDecorator(unittest.TestCase):

    def test_decorator_success_path(self):
        @add_jc_meta
        def fake_parse(data, raw=False, quiet=False, ignore_exceptions=False):
            yield {'line': 1}
            yield {'line': 2}

        results = list(fake_parse('input', ignore_exceptions=True))
        for r in results:
            self.assertIn('_jc_meta', r)
            self.assertTrue(r['_jc_meta']['success'])

    def test_decorator_error_path(self):
        @add_jc_meta
        def fake_parse(data, raw=False, quiet=False, ignore_exceptions=False):
            yield {'line': 1}
            yield (ValueError('oops'), 'bad line')

        results = list(fake_parse('input', ignore_exceptions=True))
        self.assertTrue(results[0]['_jc_meta']['success'])
        self.assertFalse(results[1]['_jc_meta']['success'])
        self.assertIn('ValueError: oops', results[1]['_jc_meta']['error'])

    def test_decorator_no_meta_when_not_ignore(self):
        @add_jc_meta
        def fake_parse(data, raw=False, quiet=False, ignore_exceptions=False):
            yield {'line': 1}

        results = list(fake_parse('input', ignore_exceptions=False))
        self.assertNotIn('_jc_meta', results[0])


class TestFullCombinationMatrix(unittest.TestCase):
    """End-to-end combination tests: every output mode × every meta mode.

    Validates that _jc_meta is present if and only if the appropriate injector
    is active, and that the structure always comes from the injector — never
    from ad-hoc construction.
    """

    def _render(self, data: Any, **renderer_kwargs: Any) -> Any:
        renderer = create_renderer(**renderer_kwargs)
        ctx = _ctx()
        output = renderer.render(data, ctx)
        return json.loads(output)

    def _render_streaming(self, data: Any, **renderer_kwargs: Any) -> Any:
        renderer = create_renderer(**renderer_kwargs)
        ctx = _ctx()
        output = renderer.render_streaming(data, ctx)
        return json.loads(output)

    def test_json_plain(self):
        parsed = self._render({'k': 'v'})
        self.assertNotIn('_jc_meta', parsed)

    def test_json_meta_out(self):
        parsed = self._render({'k': 'v'}, meta_out=True)
        self.assertIn('_jc_meta', parsed)
        self.assertEqual(parsed['_jc_meta']['parser'], 'test-parser')
        self.assertIsNotNone(parsed['_jc_meta']['timestamp'])

    def test_json_list_meta_out(self):
        parsed = self._render([{'k': 1}, {'k': 2}], meta_out=True)
        for item in parsed:
            self.assertIn('_jc_meta', item)

    def test_yaml_plain(self):
        renderer = create_renderer(yaml_output=True)
        ctx = _ctx()
        output = renderer.render({'k': 'v'}, ctx)
        self.assertNotIn('_jc_meta', output.split('\n')[0] if output else '')

    def test_yaml_meta_out(self):
        renderer = create_renderer(yaml_output=True, meta_out=True)
        ctx = _ctx()
        output = renderer.render({'k': 'v'}, ctx)
        self.assertIn('_jc_meta', output)

    def test_ndjson_plain(self):
        parsed = self._render_streaming({'k': 'v'}, streaming=True)
        self.assertNotIn('_jc_meta', parsed)

    def test_ndjson_meta_out(self):
        parsed = self._render_streaming({'k': 'v'}, streaming=True, meta_out=True)
        self.assertIn('_jc_meta', parsed)
        self.assertEqual(parsed['_jc_meta']['parser'], 'test-parser')

    def test_ndjson_qq_success(self):
        parsed = self._render_streaming({'k': 'v'}, streaming=True, ignore_exceptions=True)
        self.assertIn('_jc_meta', parsed)
        self.assertTrue(parsed['_jc_meta']['success'])

    def test_ndjson_qq_error_via_render_error(self):
        renderer = create_renderer(streaming=True, ignore_exceptions=True)
        ctx = _ctx()
        output = renderer.render_error(ValueError('x'), 'bad', ctx)
        parsed = json.loads(output)
        self.assertFalse(parsed['_jc_meta']['success'])
        self.assertIn('ValueError: x', parsed['_jc_meta']['error'])
        self.assertEqual(parsed['_jc_meta']['line'], 'bad')

    def test_meta_out_has_all_required_fields(self):
        parsed = self._render(
            {'k': 'v'},
            meta_out=True,
        )
        meta = parsed['_jc_meta']
        self.assertIn('parser', meta)
        self.assertIn('timestamp', meta)
        self.assertIn('slice_start', meta)
        self.assertIn('slice_end', meta)

    def test_meta_out_with_magic_command_context(self):
        ctx = _ctx(magic_command=['ls', '-al'], magic_command_exit=0)
        renderer = create_renderer(meta_out=True)
        output = renderer.render({'k': 'v'}, ctx)
        parsed = json.loads(output)
        self.assertEqual(parsed['_jc_meta']['magic_command'], ['ls', '-al'])
        self.assertEqual(parsed['_jc_meta']['magic_command_exit'], 0)

    def test_streaming_meta_out_combined_with_qq_error(self):
        renderer = create_renderer(streaming=True, meta_out=True, ignore_exceptions=True)
        ctx = _ctx()
        error_output = renderer.render_error(ValueError('x'), 'bad', ctx)
        parsed = json.loads(error_output)
        self.assertFalse(parsed['_jc_meta']['success'])
        self.assertIn('error', parsed['_jc_meta'])
        success_output = renderer.render_streaming({'k': 'v'}, ctx)
        parsed_ok = json.loads(success_output)
        self.assertIn('_jc_meta', parsed_ok)
        self.assertEqual(parsed_ok['_jc_meta']['parser'], 'test-parser')


class TestNoManualJcMetaInCli(unittest.TestCase):
    """Ensures cli.py never constructs _jc_meta directly.

    All metadata must come from injector classes in renderers.py.
    This test will fail if anyone re-introduces manual _jc_meta in cli.py.
    """

    def test_cli_no_jc_meta_literal(self):
        with open('/Users/pkcha/jc/jc/cli.py', 'r') as f:
            content = f.read()
        self.assertNotIn("'_jc_meta'", content)
        self.assertNotIn('"_jc_meta"', content)

    def test_streaming_no_jc_meta_construction(self):
        with open('/Users/pkcha/jc/jc/streaming.py', 'r') as f:
            content = f.read()
        lines_with_construction = [
            i + 1 for i, line in enumerate(content.splitlines())
            if '_jc_meta' in line and 'def ' not in line and '\"\"\"' not in line
            and ('{' in line or '=' in line)
        ]
        self.assertEqual(
            len(lines_with_construction), 0,
            f"streaming.py has _jc_meta construction on lines: {lines_with_construction}"
        )


class TestRendererPrintMethods(unittest.TestCase):

    def test_print_captures_output(self):
        import io
        buf = io.StringIO()
        renderer = create_renderer()
        ctx = _ctx()
        renderer.print({'k': 'v'}, ctx, file=buf)
        output = buf.getvalue().strip()
        parsed = json.loads(output)
        self.assertEqual(parsed['k'], 'v')

    def test_print_streaming_captures_output(self):
        import io
        buf = io.StringIO()
        renderer = create_renderer(streaming=True, ignore_exceptions=True)
        ctx = _ctx()
        renderer.print_streaming({'k': 'v'}, ctx, file=buf)
        output = buf.getvalue().strip()
        parsed = json.loads(output)
        self.assertTrue(parsed['_jc_meta']['success'])

    def test_print_error_captures_output(self):
        import io
        buf = io.StringIO()
        renderer = create_renderer(streaming=True, ignore_exceptions=True)
        ctx = _ctx()
        renderer.print_error(ValueError('oops'), 'bad line', ctx, file=buf)
        output = buf.getvalue().strip()
        parsed = json.loads(output)
        self.assertFalse(parsed['_jc_meta']['success'])


if __name__ == '__main__':
    unittest.main()
