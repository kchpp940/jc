import unittest
import jc.streaming


class MyTests(unittest.TestCase):

    def test_streaming_input_type_check_wrong(self):
        self.assertRaises(TypeError, jc.streaming.streaming_input_type_check, 'abc')


    def test_streaming_input_type_check_correct(self):
        self.assertEqual(jc.streaming.streaming_input_type_check(['abc']), None)


    def test_streaming_line_input_type_check_wrong(self):
        self.assertRaises(TypeError, jc.streaming.streaming_line_input_type_check, ['abc'])


    def test_streaming_line_input_type_check_correct(self):
        self.assertEqual(jc.streaming.streaming_line_input_type_check('abc'), None)


    def test_stream_success_ignore_exceptions_true(self):
        """Test stream_success with ignore_exceptions=True has success=True."""
        result = jc.streaming.stream_success({}, True)
        self.assertEqual(result['_jc_meta']['success'], True)


    def test_stream_success_ignore_exceptions_false(self):
        self.assertEqual(jc.streaming.stream_success({}, False), {})


    def test_stream_error(self):
        result = jc.streaming.stream_error(TypeError, 'this is a test')
        self.assertEqual(result['_jc_meta']['success'], False)
        self.assertEqual(result['_jc_meta']['error'], 'type: <class \'TypeError\'>')
        self.assertEqual(result['_jc_meta']['line'], 'this is a test')
        self.assertEqual(result['_jc_meta']['line_count'], 1)

    def test_stream_success_with_range(self):
        """Test that stream_success adds range info to _jc_meta."""
        range_info = {
            'line_start': 5,
            'line_end': 7,
            'line_count': 3,
            'line': 'first line',
            'lines': 'first line\nsecond line\nthird line'
        }
        result = jc.streaming.stream_success({'foo': 'bar'}, ignore_exceptions=True, range_info=range_info)
        self.assertEqual(result['foo'], 'bar')
        self.assertEqual(result['_jc_meta']['success'], True)
        self.assertEqual(result['_jc_meta']['line_start'], 5)
        self.assertEqual(result['_jc_meta']['line_end'], 7)
        self.assertEqual(result['_jc_meta']['line_count'], 3)
        self.assertEqual(result['_jc_meta']['line'], 'first line')
        self.assertEqual(result['_jc_meta']['lines'], 'first line\nsecond line\nthird line')

    def test_stream_success_no_mutation(self):
        """Test that stream_success does not mutate the input dict."""
        output = {'foo': 'bar'}
        result = jc.streaming.stream_success(output, ignore_exceptions=True)
        self.assertIsNot(result, output)
        self.assertEqual(output, {'foo': 'bar'})

    def test_add_jc_meta_positional_ignore_exceptions(self):
        """Test add_jc_meta with positional ignore_exceptions argument."""
        from jc.streaming import add_jc_meta, raise_or_yield

        @add_jc_meta
        def test_parser(data, raw=False, quiet=False, ignore_exceptions=False):
            for line in data:
                try:
                    if 'bad' in line:
                        raise ValueError('parse error')
                    yield {'content': line.strip()}
                except Exception as e:
                    yield raise_or_yield(ignore_exceptions, e, line)

        data = ['good 1', 'bad line', 'good 2']
        results = list(test_parser(data, False, False, True))
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertIn('_jc_meta', r)
            self.assertIn('success', r['_jc_meta'])
        self.assertEqual(results[0]['_jc_meta']['success'], True)
        self.assertEqual(results[0]['_jc_meta']['line'], 'good 1')
        self.assertEqual(results[2]['_jc_meta']['success'], True)
        self.assertEqual(results[2]['_jc_meta']['line'], 'good 2')
        self.assertEqual(results[1]['_jc_meta']['success'], False)
        self.assertEqual(results[1]['_jc_meta']['line'], 'bad line')

    def test_add_jc_meta_auto_line_tracking(self):
        """Test add_jc_meta automatically tracks line ranges via _LineTracker."""
        from jc.streaming import add_jc_meta, raise_or_yield

        @add_jc_meta
        def test_parser(data, raw=False, quiet=False, ignore_exceptions=False):
            for line in data:
                try:
                    yield {'data': line}
                except Exception as e:
                    yield raise_or_yield(ignore_exceptions, e, line)

        results = list(test_parser(['line1', 'line2'], ignore_exceptions=True))
        for i, r in enumerate(results):
            self.assertEqual(r['_jc_meta']['success'], True)
            self.assertIn('line_start', r['_jc_meta'])
            self.assertIn('line_end', r['_jc_meta'])
            self.assertIn('line_count', r['_jc_meta'])
            self.assertEqual(r['_jc_meta']['line'], r['data'])
            self.assertEqual(r['_jc_meta']['line_start'], i)
            self.assertEqual(r['_jc_meta']['line_end'], i)

    def test_add_jc_meta_multi_line_record(self):
        """Test add_jc_meta handles multi-line records with range tracking."""
        from jc.streaming import add_jc_meta

        @add_jc_meta
        def test_parser(data, raw=False, quiet=False, ignore_exceptions=False):
            lines_buffer = []
            for line in data:
                lines_buffer.append(line.strip())
                if len(lines_buffer) >= 3:
                    yield {'combined': ' '.join(lines_buffer)}
                    lines_buffer = []
            if lines_buffer:
                yield {'combined': ' '.join(lines_buffer)}

        test_data = ['a1', 'b1', 'c1', 'a2', 'b2', 'c2', 'a3']
        results = list(test_parser(test_data, ignore_exceptions=True))
        self.assertEqual(len(results), 3)
        # First record: lines 0-2 (3 lines)
        self.assertEqual(results[0]['_jc_meta']['line_start'], 0)
        self.assertEqual(results[0]['_jc_meta']['line_end'], 2)
        self.assertEqual(results[0]['_jc_meta']['line_count'], 3)
        self.assertIn('lines', results[0]['_jc_meta'])
        # Second record: lines 3-5 (3 lines)
        self.assertEqual(results[1]['_jc_meta']['line_start'], 3)
        self.assertEqual(results[1]['_jc_meta']['line_end'], 5)
        self.assertEqual(results[1]['_jc_meta']['line_count'], 3)
        # Third record: lines 6-6 (1 line)
        self.assertEqual(results[2]['_jc_meta']['line_start'], 6)
        self.assertEqual(results[2]['_jc_meta']['line_end'], 6)
        self.assertEqual(results[2]['_jc_meta']['line_count'], 1)

    def test_add_jc_meta_dict_yield(self):
        """Test add_jc_meta handles plain dict yield with auto range tracking."""
        from jc.streaming import add_jc_meta

        @add_jc_meta
        def test_parser(data, raw=False, quiet=False, ignore_exceptions=False):
            for line in data:
                yield {'content': line.strip()}

        results = list(test_parser(['test line'], ignore_exceptions=True))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['content'], 'test line')
        self.assertEqual(results[0]['_jc_meta']['success'], True)
        self.assertEqual(results[0]['_jc_meta']['line'], 'test line')
        self.assertEqual(results[0]['_jc_meta']['line_start'], 0)
        self.assertEqual(results[0]['_jc_meta']['line_end'], 0)

    def test_add_jc_meta_slice_offset_propagation(self):
        """Test that slice offset from line_slice propagates to _jc_meta line ranges."""
        from jc.streaming import add_jc_meta
        from jc.utils import line_slice

        @add_jc_meta
        def test_parser(data, raw=False, quiet=False, ignore_exceptions=False):
            for line in data:
                yield {'data': line.strip()}

        original_data = ['line0', 'line1', 'line2', 'line3', 'line4', 'line5']
        sliced = line_slice(original_data, 2, 5)  # lines 2,3,4
        results = list(test_parser(sliced, ignore_exceptions=True))

        self.assertEqual(len(results), 3)
        # Line numbers should be relative to original input, not the slice
        self.assertEqual(results[0]['_jc_meta']['line_start'], 2)
        self.assertEqual(results[0]['_jc_meta']['line_end'], 2)
        self.assertEqual(results[1]['_jc_meta']['line_start'], 3)
        self.assertEqual(results[1]['_jc_meta']['line_end'], 3)
        self.assertEqual(results[2]['_jc_meta']['line_start'], 4)
        self.assertEqual(results[2]['_jc_meta']['line_end'], 4)

    def test_add_jc_meta_no_meta_when_ignore_false(self):
        """Test add_jc_meta does not add _jc_meta when ignore_exceptions=False."""
        from jc.streaming import add_jc_meta

        @add_jc_meta
        def test_parser(data, raw=False, quiet=False, ignore_exceptions=False):
            for line in data:
                yield {'content': line.strip()}

        results = list(test_parser(['test'], ignore_exceptions=False))
        self.assertEqual(len(results), 1)
        self.assertNotIn('_jc_meta', results[0])


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


if __name__ == '__main__':
    unittest.main()
