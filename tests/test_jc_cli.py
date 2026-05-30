import os
import unittest
from datetime import datetime, timezone

try:
    import pygments
    from pygments.token import (Name, Number, String, Keyword)
    PYGMENTS_INSTALLED=True
except:
    PYGMENTS_INSTALLED=False

try:
    import ruamel.yaml
    RUAMELYAML_INSTALLED = True
except:
    RUAMELYAML_INSTALLED = False

from jc.cli import JcCli
from jc.cli_data import long_options_map
from jc.renderer import OutputRenderer, OUTPUT_JSON, OUTPUT_YAML, OUTPUT_NDJSON, STREAMING_ITEM_WARN_DEFAULT
import jc.parsers.url as url_parser
import jc.parsers.proc as proc_parser


class MyTests(unittest.TestCase):
    def test_cli_magic_parser(self):
        commands = {
            'jc -p systemctl list-sockets': ('--systemctl-ls', ['p'], ['systemctl', 'list-sockets']),
            'jc -p systemctl list-unit-files': ('--systemctl-luf', ['p'], ['systemctl', 'list-unit-files']),
            'jc -p pip list': ('--pip-list', ['p'], ['pip', 'list']),
            'jc -p pip3 list': ('--pip-list', ['p'], ['pip3', 'list']),
            'jc -p pip show jc': ('--pip-show', ['p'], ['pip', 'show', 'jc']),
            'jc -p pip3 show jc': ('--pip-show', ['p'], ['pip3', 'show', 'jc']),
            'jc -prd last': ('--last', ['p', 'r', 'd'], ['last']),
            'jc -prdd lastb': ('--last', ['p', 'r', 'd', 'd'], ['lastb']),
            'jc -p airport -I': ('--airport', ['p'], ['airport', '-I']),
            'jc -p -r airport -I': ('--airport', ['p', 'r'], ['airport', '-I']),
            'jc -prd airport -I': ('--airport', ['p', 'r', 'd'], ['airport', '-I']),
            'jc -p nonexistent command': (None, ['p'], ['nonexistent', 'command']),
            'jc -ap': (None, [], None),
            'jc -a arp -a': ('--arp', ['a'], ['arp', '-a']),
            'jc -v': (None, [], None),
            'jc -h': (None, [], None),
            'jc -h --arp': (None, [], None),
            'jc -h arp': ('--arp', ['h'], ['arp']),
            'jc -h arp -a': ('--arp', ['h'], ['arp', '-a']),
            'jc -v arp -a': ('--arp', ['v'], ['arp', '-a']),
            'jc --pretty dig': ('--dig', ['p'], ['dig']),
            'jc --pretty --monochrome --quiet --raw dig': ('--dig', ['p', 'm', 'q', 'r'], ['dig']),
            'jc --about --yaml-out': (None, [], None)
        }

        for command, expected in commands.items():
            cli = JcCli()
            cli.args = command.split()
            cli.magic_parser()
            resulting_attributes = (cli.magic_found_parser, cli.magic_options, cli.magic_run_command)
            self.assertEqual(expected, resulting_attributes)

    @unittest.skipIf(not PYGMENTS_INSTALLED, 'pygments library not installed')
    def test_cli_set_env_colors(self):
        if pygments.__version__.startswith('2.3.'):
            env = {
                '': {
                    Name.Tag: 'bold #ansidarkblue',
                    Keyword: '#ansidarkgray',
                    Number: '#ansipurple',
                    String: '#ansidarkgreen'
                },
                ' ': {
                    Name.Tag: 'bold #ansidarkblue',
                    Keyword: '#ansidarkgray',
                    Number: '#ansipurple',
                    String: '#ansidarkgreen'
                },
                'default,default,default,default': {
                    Name.Tag: 'bold #ansidarkblue',
                    Keyword: '#ansidarkgray',
                    Number: '#ansipurple',
                    String: '#ansidarkgreen'
                },
                'red,red,red,red': {
                    Name.Tag: 'bold #ansidarkred',
                    Keyword: '#ansidarkred',
                    Number: '#ansidarkred',
                    String: '#ansidarkred'
                },
                'red,red,yada,red': {
                    Name.Tag: 'bold #ansidarkblue',
                    Keyword: '#ansidarkgray',
                    Number: '#ansipurple',
                    String: '#ansidarkgreen'
                },
                'red,red,red': {
                    Name.Tag: 'bold #ansidarkblue',
                    Keyword: '#ansidarkgray',
                    Number: '#ansipurple',
                    String: '#ansidarkgreen'
                },
                'red,red,red,red,red,red': {
                    Name.Tag: 'bold #ansidarkblue',
                    Keyword: '#ansidarkgray',
                    Number: '#ansipurple',
                    String: '#ansidarkgreen'
                }
            }
        else:
            env = {
                '': {
                    Name.Tag: 'bold ansiblue',
                    Keyword: 'ansibrightblack',
                    Number: 'ansimagenta',
                    String: 'ansigreen'
                },
                ' ': {
                    Name.Tag: 'bold ansiblue',
                    Keyword: 'ansibrightblack',
                    Number: 'ansimagenta',
                    String: 'ansigreen'
                },
                'default,default,default,default': {
                    Name.Tag: 'bold ansiblue',
                    Keyword: 'ansibrightblack',
                    Number: 'ansimagenta',
                    String: 'ansigreen'
                },
                'red,red,red,red': {
                    Name.Tag: 'bold ansired',
                    Keyword: 'ansired',
                    Number: 'ansired',
                    String: 'ansired'
                },
                'red,red,yada,red': {
                    Name.Tag: 'bold ansiblue',
                    Keyword: 'ansibrightblack',
                    Number: 'ansimagenta',
                    String: 'ansigreen'
                },
                'red,red,red': {
                    Name.Tag: 'bold ansiblue',
                    Keyword: 'ansibrightblack',
                    Number: 'ansimagenta',
                    String: 'ansigreen'
                },
                'red,red,red,red,red,red': {
                    Name.Tag: 'bold ansiblue',
                    Keyword: 'ansibrightblack',
                    Number: 'ansimagenta',
                    String: 'ansigreen'
                }
            }

        for jc_colors, expected_colors in env.items():
            cli = JcCli()
            os.environ["JC_COLORS"] = jc_colors
            cli.set_custom_colors()
            self.assertEqual(cli.custom_colors, expected_colors)

    @unittest.skipIf(not PYGMENTS_INSTALLED, 'pygments library not installed')
    def test_cli_json_out(self):
        test_input = [
            None,
            {},
            [],
            '',
            {"key1": "value1", "key2": 2, "key3": None, "key4": 3.14, "key5": True},
        ]

        if pygments.__version__.startswith('2.3.'):
            expected_output = [
                '\x1b[30;01mnull\x1b[39;00m',
                '{}',
                '[]',
                '\x1b[32m""\x1b[39m',
                '{\x1b[34;01m"key1"\x1b[39;00m:\x1b[32m"value1"\x1b[39m,\x1b[34;01m"key2"\x1b[39;00m:\x1b[35m2\x1b[39m,\x1b[34;01m"key3"\x1b[39;00m:\x1b[30;01mnull\x1b[39;00m,\x1b[34;01m"key4"\x1b[39;00m:\x1b[35m3.14\x1b[39m,\x1b[34;01m"key5"\x1b[39;00m:\x1b[30;01mtrue\x1b[39;00m}'
            ]
        else:
            expected_output = [
                '\x1b[90mnull\x1b[39m',
                '{}',
                '[]',
                '\x1b[32m""\x1b[39m',
                '{\x1b[34;01m"key1"\x1b[39;00m:\x1b[32m"value1"\x1b[39m,\x1b[34;01m"key2"\x1b[39;00m:\x1b[35m2\x1b[39m,\x1b[34;01m"key3"\x1b[39;00m:\x1b[90mnull\x1b[39m,\x1b[34;01m"key4"\x1b[39;00m:\x1b[35m3.14\x1b[39m,\x1b[34;01m"key5"\x1b[39;00m:\x1b[90mtrue\x1b[39m}'
            ]

        for test_dict, expected_json in zip(test_input, expected_output):
            cli = JcCli()
            os.environ["JC_COLORS"] = "default,default,default,default"
            cli.set_custom_colors()
            cli.data_out = test_dict
            cli.ndjson_output = False
            cli.yaml_output = False
            self.assertEqual(cli.render_output(test_dict), expected_json)

    @unittest.skipIf(not PYGMENTS_INSTALLED, 'pygments library not installed')
    def test_cli_json_out_mono(self):
        test_input = [
            None,
            {},
            [],
            '',
            {"key1": "value1", "key2": 2, "key3": None, "key4": 3.14, "key5": True},
        ]

        expected_output = [
            'null',
            '{}',
            '[]',
            '""',
            '{"key1":"value1","key2":2,"key3":null,"key4":3.14,"key5":true}'
        ]

        for test_dict, expected_json in zip(test_input, expected_output):
            cli = JcCli()
            cli.set_custom_colors()
            cli.mono = True
            cli.data_out = test_dict
            cli.ndjson_output = False
            cli.yaml_output = False
            self.assertEqual(cli.render_output(test_dict), expected_json)

    @unittest.skipIf(not PYGMENTS_INSTALLED, 'pygments library not installed')
    def test_cli_json_out_pretty(self):
        test_input = [
            {"key1": "value1", "key2": 2, "key3": None, "key4": 3.14, "key5": True},
            {"key1": [{"subkey1": "subvalue1"}, {"subkey2": [1, 2, 3]}], "key2": True}
        ]

        if pygments.__version__.startswith('2.3.'):
            expected_output = [
                '{\n  \x1b[34;01m"key1"\x1b[39;00m: \x1b[32m"value1"\x1b[39m,\n  \x1b[34;01m"key2"\x1b[39;00m: \x1b[35m2\x1b[39m,\n  \x1b[34;01m"key3"\x1b[39;00m: \x1b[30;01mnull\x1b[39;00m,\n  \x1b[34;01m"key4"\x1b[39;00m: \x1b[35m3.14\x1b[39m,\n  \x1b[34;01m"key5"\x1b[39;00m: \x1b[30;01mtrue\x1b[39;00m\n}',
                '{\n  \x1b[34;01m"key1"\x1b[39;00m: [\n    {\n      \x1b[34;01m"subkey1"\x1b[39;00m: \x1b[32m"subvalue1"\x1b[39m\n    },\n    {\n      \x1b[34;01m"subkey2"\x1b[39;00m: [\n        \x1b[35m1\x1b[39m,\n        \x1b[35m2\x1b[39m,\n        \x1b[35m3\x1b[39m\n      ]\n    }\n  ],\n  \x1b[34;01m"key2"\x1b[39;00m: \x1b[30;01mtrue\x1b[39;00m\n}'
            ]
        else:
            expected_output = [
                '{\n  \x1b[34;01m"key1"\x1b[39;00m: \x1b[32m"value1"\x1b[39m,\n  \x1b[34;01m"key2"\x1b[39;00m: \x1b[35m2\x1b[39m,\n  \x1b[34;01m"key3"\x1b[39;00m: \x1b[90mnull\x1b[39m,\n  \x1b[34;01m"key4"\x1b[39;00m: \x1b[35m3.14\x1b[39m,\n  \x1b[34;01m"key5"\x1b[39;00m: \x1b[90mtrue\x1b[39m\n}',
                '{\n  \x1b[34;01m"key1"\x1b[39;00m: [\n    {\n      \x1b[34;01m"subkey1"\x1b[39;00m: \x1b[32m"subvalue1"\x1b[39m\n    },\n    {\n      \x1b[34;01m"subkey2"\x1b[39;00m: [\n        \x1b[35m1\x1b[39m,\n        \x1b[35m2\x1b[39m,\n        \x1b[35m3\x1b[39m\n      ]\n    }\n  ],\n  \x1b[34;01m"key2"\x1b[39;00m: \x1b[90mtrue\x1b[39m\n}'
            ]

        for test_dict, expected_json in zip(test_input, expected_output):
            cli = JcCli()
            cli.pretty = True
            cli.set_custom_colors()
            cli.data_out = test_dict
            cli.ndjson_output = False
            cli.yaml_output = False
            self.assertEqual(cli.render_output(test_dict), expected_json)

    @unittest.skipIf(PYGMENTS_INSTALLED, 'pygments library installed')
    def test_cli_json_out_pretty_no_pygments(self):
        test_input = [
            {"key1": "value1", "key2": 2, "key3": None, "key4": 3.14, "key5": True},
            {"key1": [{"subkey1": "subvalue1"}, {"subkey2": [1, 2, 3]}], "key2": True}
        ]

        expected_output = [
            '{\n  "key1": "value1",\n  "key2": 2,\n  "key3": null,\n  "key4": 3.14,\n  "key5": true\n}',
            '{\n  "key1": [\n    {\n      "subkey1": "subvalue1"\n    },\n    {\n      "subkey2": [\n        1,\n        2,\n        3\n      ]\n    }\n  ],\n  "key2": true\n}'
        ]

        for test_dict, expected_json in zip(test_input, expected_output):
            cli = JcCli()
            cli.pretty = True
            cli.set_custom_colors()
            cli.data_out = test_dict
            cli.ndjson_output = False
            cli.yaml_output = False
            self.assertEqual(cli.render_output(test_dict), expected_json)

    @unittest.skipIf(not PYGMENTS_INSTALLED, 'pygments library not installed')
    def test_cli_yaml_out(self):
        test_input = [
            None,
            {},
            [],
            '',
            {"key1": "value1", "key2": 2, "key3": None, "key4": 3.14, "key5": True},
        ]

        if pygments.__version__.startswith('2.3.'):
            expected_output = [
                '---\n...',
                '--- {}',
                '--- []',
                "--- \x1b[32m'\x1b[39m\x1b[32m'\x1b[39m",
                '---\nkey1: value1\nkey2: 2\nkey3:\nkey4: 3.14\nkey5: true'
            ]
        else:
            expected_output = [
                '---\n...',
                '--- {}',
                '--- []',
                "--- \x1b[32m'\x1b[39m\x1b[32m'\x1b[39m",
                '---\n\x1b[34;01mkey1\x1b[39;00m: value1\n\x1b[34;01mkey2\x1b[39;00m: 2\n\x1b[34;01mkey3\x1b[39;00m:\n\x1b[34;01mkey4\x1b[39;00m: 3.14\n\x1b[34;01mkey5\x1b[39;00m: true'
            ]

        for test_dict, expected_json in zip(test_input, expected_output):
            cli = JcCli()
            os.environ["JC_COLORS"] = "default,default,default,default"
            cli.set_custom_colors()
            cli.data_out = test_dict
            cli.ndjson_output = False
            cli.yaml_output = True
            self.assertEqual(cli.render_output(test_dict), expected_json)

    @unittest.skipIf(not RUAMELYAML_INSTALLED, 'ruamel.yaml library not installed')
    def test_cli_yaml_out_mono(self):
        test_input = [
            None,
            {},
            [],
            '',
            {'ipv6': 'fe80::5a37:f41:1076:ba24:'},  # test for colon at the end
            {"key1": "value1", "key2": 2, "key3": None, "key4": 3.14, "key5": True},
        ]

        expected_output = [
            '---\n...',
            '--- {}',
            '--- []',
            "--- ''",
            "---\nipv6: 'fe80::5a37:f41:1076:ba24:'",
            '---\nkey1: value1\nkey2: 2\nkey3:\nkey4: 3.14\nkey5: true'
        ]

        for test_dict, expected_json in zip(test_input, expected_output):
            cli = JcCli()
            cli.set_custom_colors()
            cli.mono = True
            cli.data_out = test_dict
            cli.ndjson_output = False
            cli.yaml_output = True
            self.assertEqual(cli.render_output(test_dict), expected_json)

    def test_cli_about_jc(self):
        cli = JcCli()
        self.assertEqual(cli.about_jc()['name'], 'jc')
        self.assertGreaterEqual(cli.about_jc()['parser_count'], 55)
        self.assertEqual(cli.about_jc()['parser_count'], len(cli.about_jc()['parsers']))

    def test_cli_parsers_text(self):
        cli = JcCli()
        self.assertIsNot(cli.parsers_text, '')

    def test_add_meta_to_simple_dict(self):
        cli = JcCli()
        cli.data_out = {'a': 1, 'b': 2}
        cli.run_timestamp = datetime(2022, 8, 5, 0, 37, 9, 273349, tzinfo=timezone.utc)
        cli.magic_returncode = 2
        cli.magic_run_command = ['ping', '-c3', '192.168.1.123']
        cli.parser_name = 'ping'
        expected = {'a': 1, 'b': 2, '_jc_meta': {'parser': 'ping', 'magic_command': ['ping', '-c3', '192.168.1.123'], 'magic_command_exit': 2, 'timestamp': 1659659829.273349, 'slice_start': None, 'slice_end': None}}
        cli.add_metadata_to_output()
        self.assertEqual(cli.data_out, expected)

    def test_add_meta_to_simple_list(self):
        cli = JcCli()
        cli.data_out = [{'a': 1, 'b': 2},{'a': 3, 'b': 4}]
        cli.run_timestamp = datetime(2022, 8, 5, 0, 37, 9, 273349, tzinfo=timezone.utc)
        cli.magic_returncode = 2
        cli.magic_run_command = ['ping', '-c3', '192.168.1.123']
        cli.parser_name = 'ping'
        expected = [{'a': 1, 'b': 2, '_jc_meta': {'parser': 'ping', 'magic_command': ['ping', '-c3', '192.168.1.123'], 'magic_command_exit': 2, 'timestamp': 1659659829.273349, 'slice_start': None, 'slice_end': None}}, {'a': 3, 'b': 4, '_jc_meta': {'parser': 'ping', 'magic_command': ['ping', '-c3', '192.168.1.123'], 'magic_command_exit': 2, 'timestamp': 1659659829.273349, 'slice_start': None, 'slice_end': None}}]
        cli.add_metadata_to_output()
        self.assertEqual(cli.data_out, expected)

    def test_add_meta_to_dict_existing_meta(self):
        cli = JcCli()
        cli.magic_run_command = ['ping', '-c3', '192.168.1.123']
        cli.magic_returncode = 2
        cli.data_out = {'a': 1, 'b': 2, '_jc_meta': {'foo': 'bar'}}
        cli.run_timestamp = datetime(2022, 8, 5, 0, 37, 9, 273349, tzinfo=timezone.utc)
        cli.parser_name = 'ping'
        expected = {'a': 1, 'b': 2, '_jc_meta': {'foo': 'bar', 'parser': 'ping', 'magic_command': ['ping', '-c3', '192.168.1.123'], 'magic_command_exit': 2, 'timestamp': 1659659829.273349, 'slice_start': None, 'slice_end': None}}
        cli.add_metadata_to_output()
        self.assertEqual(cli.data_out, expected)

    def test_add_meta_to_list_existing_meta(self):
        cli = JcCli()
        cli.data_out = [{'a': 1, 'b': 2, '_jc_meta': {'foo': 'bar'}},{'a': 3, 'b': 4, '_jc_meta': {'foo': 'bar'}}]
        cli.run_timestamp = datetime(2022, 8, 5, 0, 37, 9, 273349, tzinfo=timezone.utc)
        cli.magic_returncode = 2
        cli.magic_run_command = ['ping', '-c3', '192.168.1.123']
        cli.parser_name = 'ping'
        expected = [{'a': 1, 'b': 2, '_jc_meta': {'foo': 'bar', 'parser': 'ping', 'magic_command': ['ping', '-c3', '192.168.1.123'], 'magic_command_exit': 2, 'timestamp': 1659659829.273349, 'slice_start': None, 'slice_end': None}}, {'a': 3, 'b': 4, '_jc_meta': {'foo': 'bar', 'parser': 'ping', 'magic_command': ['ping', '-c3', '192.168.1.123'], 'magic_command_exit': 2, 'timestamp': 1659659829.273349, 'slice_start': None, 'slice_end': None}}]
        cli.add_metadata_to_output()
        self.assertEqual(cli.data_out, expected)

    def test_slice_none_str(self):
        cli = JcCli()
        cli.slice_start = None
        cli.slice_end = None
        cli.data_in = '''\
        row0
        row1
        row2
        row3
        row4
        row5'''
        expected = '''\
        row0
        row1
        row2
        row3
        row4
        row5'''
        cli.slicer()
        self.assertEqual(cli.data_in, expected)

    def test_slice_positive_str(self):
        cli = JcCli()
        cli.slice_start = 1
        cli.slice_end = 5
        cli.data_in = '''\
        row0
        row1
        row2
        row3
        row4
        row5'''
        expected = '''\
        row1
        row2
        row3
        row4'''
        cli.slicer()
        self.assertEqual(cli.data_in, expected)

    def test_slice_negative_str(self):
        cli = JcCli()
        cli.slice_start = 1
        cli.slice_end = -1
        cli.data_in = '''\
        row0
        row1
        row2
        row3
        row4
        row5'''
        expected = '''\
        row1
        row2
        row3
        row4'''
        cli.slicer()
        self.assertEqual(cli.data_in, expected)

    def test_slice_none_iter(self):
        cli = JcCli()
        cli.slice_start = None
        cli.slice_end = None
        cli.data_in = [
            'row0',
            'row1',
            'row2',
            'row3',
            'row4',
            'row5'
        ]
        expected = [
            'row0',
            'row1',
            'row2',
            'row3',
            'row4',
            'row5'
        ]
        cli.slicer()
        self.assertEqual(cli.data_in, expected)

    def test_slice_positive_iter(self):
        cli = JcCli()
        cli.slice_start = 1
        cli.slice_end = 5
        cli.data_in = [
            'row0',
            'row1',
            'row2',
            'row3',
            'row4',
            'row5'
        ]
        expected = [
            'row1',
            'row2',
            'row3',
            'row4'
        ]
        cli.slicer()
        self.assertEqual(list(cli.data_in), expected)

    def test_slice_negative_iter(self):
        cli = JcCli()
        cli.slice_start = 1
        cli.slice_end = -1
        cli.data_in = [
            'row0',
            'row1',
            'row2',
            'row3',
            'row4',
            'row5'
        ]
        expected = [
            'row1',
            'row2',
            'row3',
            'row4'
        ]
        cli.slicer()
        self.assertEqual(list(cli.data_in), expected)

    def test_slurp_standard(self):
        cli = JcCli()
        cli.parser_module = url_parser
        cli.data_in = '''http://www.google.com
            https://www.kelly.com/testing
            https://mail.apple.com'''
        expected = [{"url":"http://www.google.com","scheme":"http","netloc":"www.google.com","path":None,"parent":None,"filename":None,"stem":None,"extension":None,"path_list":None,"query":None,"query_obj":None,"fragment":None,"username":None,"password":None,"hostname":"www.google.com","port":None,"encoded":{"url":"http://www.google.com","scheme":"http","netloc":"www.google.com","path":None,"parent":None,"filename":None,"stem":None,"extension":None,"path_list":None,"query":None,"fragment":None,"username":None,"password":None,"hostname":"www.google.com","port":None},"decoded":{"url":"http://www.google.com","scheme":"http","netloc":"www.google.com","path":None,"parent":None,"filename":None,"stem":None,"extension":None,"path_list":None,"query":None,"fragment":None,"username":None,"password":None,"hostname":"www.google.com","port":None}},{"url":"https://www.kelly.com/testing","scheme":"https","netloc":"www.kelly.com","path":"/testing","parent":"/","filename":"testing","stem":"testing","extension":None,"path_list":["testing"],"query":None,"query_obj":None,"fragment":None,"username":None,"password":None,"hostname":"www.kelly.com","port":None,"encoded":{"url":"https://www.kelly.com/testing","scheme":"https","netloc":"www.kelly.com","path":"/testing","parent":"/","filename":"testing","stem":"testing","extension":None,"path_list":["testing"],"query":None,"fragment":None,"username":None,"password":None,"hostname":"www.kelly.com","port":None},"decoded":{"url":"https://www.kelly.com/testing","scheme":"https","netloc":"www.kelly.com","path":"/testing","parent":"/","filename":"testing","stem":"testing","extension":None,"path_list":["testing"],"query":None,"fragment":None,"username":None,"password":None,"hostname":"www.kelly.com","port":None}},{"url":"https://mail.apple.com","scheme":"https","netloc":"mail.apple.com","path":None,"parent":None,"filename":None,"stem":None,"extension":None,"path_list":None,"query":None,"query_obj":None,"fragment":None,"username":None,"password":None,"hostname":"mail.apple.com","port":None,"encoded":{"url":"https://mail.apple.com","scheme":"https","netloc":"mail.apple.com","path":None,"parent":None,"filename":None,"stem":None,"extension":None,"path_list":None,"query":None,"fragment":None,"username":None,"password":None,"hostname":"mail.apple.com","port":None},"decoded":{"url":"https://mail.apple.com","scheme":"https","netloc":"mail.apple.com","path":None,"parent":None,"filename":None,"stem":None,"extension":None,"path_list":None,"query":None,"fragment":None,"username":None,"password":None,"hostname":"mail.apple.com","port":None}}]
        cli.create_slurp_output()
        self.assertEqual(cli.data_out, expected)

    def test_slurp_standard_with_meta_out(self):
        cli = JcCli()
        cli.meta_out = True
        cli.parser_module = url_parser
        cli.data_in = '''http://www.google.com
            https://www.kelly.com/testing
            https://mail.apple.com'''
        expected = {"result":[{"url":"http://www.google.com","scheme":"http","netloc":"www.google.com","path":None,"parent":None,"filename":None,"stem":None,"extension":None,"path_list":None,"query":None,"query_obj":None,"fragment":None,"username":None,"password":None,"hostname":"www.google.com","port":None,"encoded":{"url":"http://www.google.com","scheme":"http","netloc":"www.google.com","path":None,"parent":None,"filename":None,"stem":None,"extension":None,"path_list":None,"query":None,"fragment":None,"username":None,"password":None,"hostname":"www.google.com","port":None},"decoded":{"url":"http://www.google.com","scheme":"http","netloc":"www.google.com","path":None,"parent":None,"filename":None,"stem":None,"extension":None,"path_list":None,"query":None,"fragment":None,"username":None,"password":None,"hostname":"www.google.com","port":None}},{"url":"https://www.kelly.com/testing","scheme":"https","netloc":"www.kelly.com","path":"/testing","parent":"/","filename":"testing","stem":"testing","extension":None,"path_list":["testing"],"query":None,"query_obj":None,"fragment":None,"username":None,"password":None,"hostname":"www.kelly.com","port":None,"encoded":{"url":"https://www.kelly.com/testing","scheme":"https","netloc":"www.kelly.com","path":"/testing","parent":"/","filename":"testing","stem":"testing","extension":None,"path_list":["testing"],"query":None,"fragment":None,"username":None,"password":None,"hostname":"www.kelly.com","port":None},"decoded":{"url":"https://www.kelly.com/testing","scheme":"https","netloc":"www.kelly.com","path":"/testing","parent":"/","filename":"testing","stem":"testing","extension":None,"path_list":["testing"],"query":None,"fragment":None,"username":None,"password":None,"hostname":"www.kelly.com","port":None}},{"url":"https://mail.apple.com","scheme":"https","netloc":"mail.apple.com","path":None,"parent":None,"filename":None,"stem":None,"extension":None,"path_list":None,"query":None,"query_obj":None,"fragment":None,"username":None,"password":None,"hostname":"mail.apple.com","port":None,"encoded":{"url":"https://mail.apple.com","scheme":"https","netloc":"mail.apple.com","path":None,"parent":None,"filename":None,"stem":None,"extension":None,"path_list":None,"query":None,"fragment":None,"username":None,"password":None,"hostname":"mail.apple.com","port":None},"decoded":{"url":"https://mail.apple.com","scheme":"https","netloc":"mail.apple.com","path":None,"parent":None,"filename":None,"stem":None,"extension":None,"path_list":None,"query":None,"fragment":None,"username":None,"password":None,"hostname":"mail.apple.com","port":None}}],"_jc_meta":{"parser":"url","timestamp":1659659829.273349,"slice_start":None,"slice_end":None,"input_list":["http://www.google.com","https://www.kelly.com/testing","https://mail.apple.com"]}}
        cli.create_slurp_output()
        cli.run_timestamp = datetime(2022, 8, 5, 0, 37, 9, 273349, tzinfo=timezone.utc)
        cli.parser_name = 'url'
        cli.add_metadata_to_output()
        self.assertEqual(cli.data_out, expected)

    def test_slurp_proc(self):
        cli = JcCli()
        cli.parser_module = proc_parser
        cli.inputlist = ['/proc/stat', '/proc/cpuinfo']
        cli.data_in = [
'''cpu  6002 152 8398 3444436 448 0 1174 0 0 0
cpu0 2784 137 4367 1732802 225 0 221 0 0 0
cpu1 3218 15 4031 1711634 223 0 953 0 0 0
intr 2496709 18 73 0 0 0 0 0 0 1 0 0 0 18 0 0 0 4219 37341 423366 128490 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 9063 2363 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
ctxt 4622716
btime 1662154781
processes 9831
procs_running 1
procs_blocked 0
softirq 3478985 35230 1252057 3467 128583 51014 0 171199 1241297 0 596138
''',
'''processor	: 0
vendor_id	: GenuineIntel
cpu family	: 6
model		: 142
model name	: Intel(R) Core(TM) i5-7360U CPU @ 2.30GHz
stepping	: 9
cpu MHz		: 2303.998
cache size	: 4096 KB
physical id	: 0
siblings	: 1
core id		: 0
cpu cores	: 1
apicid		: 0
initial apicid	: 0
fpu		: yes
fpu_exception	: yes
cpuid level	: 22
wp		: yes
flags		: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ht syscall nx rdtscp lm constant_tsc rep_good nopl xtopology nonstop_tsc eagerfpu pni pclmulqdq monitor ssse3 cx16 pcid sse4_1 sse4_2 x2apic movbe popcnt aes xsave avx rdrand hypervisor lahf_lm abm 3dnowprefetch fsgsbase avx2 invpcid rdseed clflushopt md_clear flush_l1d
bogomips	: 4607.99
clflush size	: 64
cache_alignment	: 64
address sizes	: 39 bits physical, 48 bits virtual
power management:
'''
        ]
        expected = [{"cpu":{"user":6002,"nice":152,"system":8398,"idle":3444436,"iowait":448,"irq":0,"softirq":1174,"steal":0,"guest":0,"guest_nice":0},"cpu0":{"user":2784,"nice":137,"system":4367,"idle":1732802,"iowait":225,"irq":0,"softirq":221,"steal":0,"guest":0,"guest_nice":0},"cpu1":{"user":3218,"nice":15,"system":4031,"idle":1711634,"iowait":223,"irq":0,"softirq":953,"steal":0,"guest":0,"guest_nice":0},"interrupts":[2496709,18,73,0,0,0,0,0,0,1,0,0,0,18,0,0,0,4219,37341,423366,128490,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,9063,2363,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],"context_switches":4622716,"boot_time":1662154781,"processes":9831,"processes_running":1,"processes_blocked":0,"softirq":[3478985,35230,1252057,3467,128583,51014,0,171199,1241297,0,596138],"_file":"/proc/stat"},[{"processor":0,"vendor_id":"GenuineIntel","cpu family":6,"model":142,"model name":"Intel(R) Core(TM) i5-7360U CPU @ 2.30GHz","stepping":9,"cpu MHz":2303.998,"cache size":"4096 KB","physical id":0,"siblings":1,"core id":0,"cpu cores":1,"apicid":0,"initial apicid":0,"fpu":True,"fpu_exception":True,"cpuid level":22,"wp":True,"flags":["fpu","vme","de","pse","tsc","msr","pae","mce","cx8","apic","sep","mtrr","pge","mca","cmov","pat","pse36","clflush","mmx","fxsr","sse","sse2","ht","syscall","nx","rdtscp","lm","constant_tsc","rep_good","nopl","xtopology","nonstop_tsc","eagerfpu","pni","pclmulqdq","monitor","ssse3","cx16","pcid","sse4_1","sse4_2","x2apic","movbe","popcnt","aes","xsave","avx","rdrand","hypervisor","lahf_lm","abm","3dnowprefetch","fsgsbase","avx2","invpcid","rdseed","clflushopt","md_clear","flush_l1d"],"bogomips":4607.99,"clflush size":64,"cache_alignment":64,"address sizes":"39 bits physical, 48 bits virtual","power management":None,"address_size_physical":39,"address_size_virtual":48,"cache_size_num":4096,"cache_size_unit":"KB","_file":"/proc/cpuinfo"}]]
        cli.quiet = True
        cli.create_slurp_output()
        self.assertEqual(cli.data_out, expected)

    def test_slurp_proc_with_meta_out(self):
        cli = JcCli()
        cli.meta_out = True
        cli.parser_module = proc_parser
        cli.magic_run_command = ['/proc/stat', '/proc/cpuinfo']
        cli.magic_returncode = 0
        cli.inputlist = ['/proc/stat', '/proc/cpuinfo']
        cli.data_in = [
'''cpu  6002 152 8398 3444436 448 0 1174 0 0 0
cpu0 2784 137 4367 1732802 225 0 221 0 0 0
cpu1 3218 15 4031 1711634 223 0 953 0 0 0
intr 2496709 18 73 0 0 0 0 0 0 1 0 0 0 18 0 0 0 4219 37341 423366 128490 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 9063 2363 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
ctxt 4622716
btime 1662154781
processes 9831
procs_running 1
procs_blocked 0
softirq 3478985 35230 1252057 3467 128583 51014 0 171199 1241297 0 596138
''',
'''processor	: 0
vendor_id	: GenuineIntel
cpu family	: 6
model		: 142
model name	: Intel(R) Core(TM) i5-7360U CPU @ 2.30GHz
stepping	: 9
cpu MHz		: 2303.998
cache size	: 4096 KB
physical id	: 0
siblings	: 1
core id		: 0
cpu cores	: 1
apicid		: 0
initial apicid	: 0
fpu		: yes
fpu_exception	: yes
cpuid level	: 22
wp		: yes
flags		: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ht syscall nx rdtscp lm constant_tsc rep_good nopl xtopology nonstop_tsc eagerfpu pni pclmulqdq monitor ssse3 cx16 pcid sse4_1 sse4_2 x2apic movbe popcnt aes xsave avx rdrand hypervisor lahf_lm abm 3dnowprefetch fsgsbase avx2 invpcid rdseed clflushopt md_clear flush_l1d
bogomips	: 4607.99
clflush size	: 64
cache_alignment	: 64
address sizes	: 39 bits physical, 48 bits virtual
power management:
'''
        ]
        expected = {"result":[{"cpu":{"user":6002,"nice":152,"system":8398,"idle":3444436,"iowait":448,"irq":0,"softirq":1174,"steal":0,"guest":0,"guest_nice":0},"cpu0":{"user":2784,"nice":137,"system":4367,"idle":1732802,"iowait":225,"irq":0,"softirq":221,"steal":0,"guest":0,"guest_nice":0},"cpu1":{"user":3218,"nice":15,"system":4031,"idle":1711634,"iowait":223,"irq":0,"softirq":953,"steal":0,"guest":0,"guest_nice":0},"interrupts":[2496709,18,73,0,0,0,0,0,0,1,0,0,0,18,0,0,0,4219,37341,423366,128490,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,9063,2363,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],"context_switches":4622716,"boot_time":1662154781,"processes":9831,"processes_running":1,"processes_blocked":0,"softirq":[3478985,35230,1252057,3467,128583,51014,0,171199,1241297,0,596138],"_file":"/proc/stat"},[{"processor":0,"vendor_id":"GenuineIntel","cpu family":6,"model":142,"model name":"Intel(R) Core(TM) i5-7360U CPU @ 2.30GHz","stepping":9,"cpu MHz":2303.998,"cache size":"4096 KB","physical id":0,"siblings":1,"core id":0,"cpu cores":1,"apicid":0,"initial apicid":0,"fpu":True,"fpu_exception":True,"cpuid level":22,"wp":True,"flags":["fpu","vme","de","pse","tsc","msr","pae","mce","cx8","apic","sep","mtrr","pge","mca","cmov","pat","pse36","clflush","mmx","fxsr","sse","sse2","ht","syscall","nx","rdtscp","lm","constant_tsc","rep_good","nopl","xtopology","nonstop_tsc","eagerfpu","pni","pclmulqdq","monitor","ssse3","cx16","pcid","sse4_1","sse4_2","x2apic","movbe","popcnt","aes","xsave","avx","rdrand","hypervisor","lahf_lm","abm","3dnowprefetch","fsgsbase","avx2","invpcid","rdseed","clflushopt","md_clear","flush_l1d"],"bogomips":4607.99,"clflush size":64,"cache_alignment":64,"address sizes":"39 bits physical, 48 bits virtual","power management":None,"address_size_physical":39,"address_size_virtual":48,"cache_size_num":4096,"cache_size_unit":"KB","_file":"/proc/cpuinfo"}]],"_jc_meta":{"parser":"proc","timestamp":1659659829.273349,"slice_start":None,"slice_end":None,"magic_command":["/proc/stat","/proc/cpuinfo"],"magic_command_exit":0,"input_list":["/proc/stat","/proc/cpuinfo"]}}
        cli.quiet = True
        cli.create_slurp_output()
        cli.run_timestamp = datetime(2022, 8, 5, 0, 37, 9, 273349, tzinfo=timezone.utc)
        cli.parser_name = 'proc'
        cli.add_metadata_to_output()
        self.assertEqual(cli.data_out, expected)

    def test_cli_ndjson_out_dict(self):
        test_input = {"key1": "value1", "key2": 2, "key3": None, "key4": 3.14, "key5": True}
        expected_output = '{"key1":"value1","key2":2,"key3":null,"key4":3.14,"key5":true}'
        cli = JcCli()
        cli.mono = True
        cli.data_out = test_input
        cli.ndjson_output = True
        cli.yaml_output = False
        self.assertEqual(cli.render_output(test_input), expected_output)

    def test_cli_ndjson_out_list(self):
        test_input = [{"name": "foo", "val": 1}, {"name": "bar", "val": 2}]
        expected_output = '{"name":"foo","val":1}\n{"name":"bar","val":2}'
        cli = JcCli()
        cli.mono = True
        cli.data_out = test_input
        cli.ndjson_output = True
        cli.yaml_output = False
        self.assertEqual(cli.render_output(test_input), expected_output)

    def test_cli_ndjson_out_empty_list(self):
        cli = JcCli()
        cli.mono = True
        cli.data_out = []
        cli.ndjson_output = True
        cli.yaml_output = False
        self.assertEqual(cli.render_output([]), '')

    def test_cli_ndjson_out_none(self):
        cli = JcCli()
        cli.mono = True
        cli.data_out = None
        cli.ndjson_output = True
        cli.yaml_output = False
        self.assertEqual(cli.render_output(None), 'null')

    def test_cli_ndjson_out_empty_string(self):
        cli = JcCli()
        cli.mono = True
        cli.data_out = ''
        cli.ndjson_output = True
        cli.yaml_output = False
        self.assertEqual(cli.render_output(''), '""')

    def test_cli_ndjson_out_empty_dict(self):
        cli = JcCli()
        cli.mono = True
        cli.data_out = {}
        cli.ndjson_output = True
        cli.yaml_output = False
        self.assertEqual(cli.render_output({}), '{}')

    def test_cli_ndjson_out_list_with_nested(self):
        test_input = [
            {"key1": "value1", "nested": {"a": 1}},
            {"key1": "value2", "nested": {"a": 2}}
        ]
        expected_output = '{"key1":"value1","nested":{"a":1}}\n{"key1":"value2","nested":{"a":2}}'
        cli = JcCli()
        cli.mono = True
        cli.data_out = test_input
        cli.ndjson_output = True
        cli.yaml_output = False
        self.assertEqual(cli.render_output(test_input), expected_output)

    def test_cli_ndjson_forces_mono(self):
        cli = JcCli()
        cli.args = ['jc', '-n', '--date']
        cli.magic_parser()
        cli.options.extend(cli.magic_options)
        for opt in cli.args:
            if opt in long_options_map:
                cli.options.extend(long_options_map[opt][0])
            if opt.startswith('-') and not opt.startswith('--'):
                cli.options.extend(opt[1:])
        cli.ndjson_output = 'n' in cli.options
        cli.set_mono()
        cli.set_custom_colors()
        if cli.ndjson_output:
            cli.mono = True
        self.assertTrue(cli.mono)

    def test_renderer_invalid_format(self):
        with self.assertRaises(ValueError):
            OutputRenderer(output_format='invalid')

    def test_renderer_ndjson_forces_mono(self):
        renderer = OutputRenderer(output_format=OUTPUT_NDJSON, mono=False)
        self.assertTrue(renderer.mono)

    def test_renderer_ndjson_dict(self):
        test_input = {"key1": "value1", "key2": 2}
        renderer = OutputRenderer(output_format=OUTPUT_NDJSON, mono=True)
        self.assertEqual(renderer.render(test_input), '{"key1":"value1","key2":2}')

    def test_renderer_ndjson_list(self):
        test_input = [{"name": "foo"}, {"name": "bar"}]
        renderer = OutputRenderer(output_format=OUTPUT_NDJSON, mono=True)
        self.assertEqual(renderer.render(test_input), '{"name":"foo"}\n{"name":"bar"}')

    def test_renderer_json_compact(self):
        test_input = {"key1": "value1", "key2": 2}
        renderer = OutputRenderer(output_format=OUTPUT_JSON, mono=True)
        self.assertEqual(renderer.render(test_input), '{"key1":"value1","key2":2}')

    def test_renderer_json_pretty(self):
        test_input = {"key1": "value1", "key2": 2}
        renderer = OutputRenderer(output_format=OUTPUT_JSON, pretty=True, mono=True)
        self.assertEqual(renderer.render(test_input), '{\n  "key1": "value1",\n  "key2": 2\n}')

    @unittest.skipIf(not RUAMELYAML_INSTALLED, 'ruamel.yaml library not installed')
    def test_renderer_yaml(self):
        test_input = {"key1": "value1", "key2": 2}
        renderer = OutputRenderer(output_format=OUTPUT_YAML, mono=True)
        self.assertEqual(renderer.render(test_input), '---\nkey1: value1\nkey2: 2')

    def test_renderer_streaming_error_object(self):
        error_obj = {
            '_jc_meta': {
                'success': False,
                'error': 'ParseError: Invalid line',
                'line': 'bad data'
            }
        }
        renderer = OutputRenderer(output_format=OUTPUT_NDJSON, mono=True)
        result = renderer.render(error_obj)
        self.assertIn('_jc_meta', result)
        self.assertIn('success', result)
        self.assertIn('false', result)
        self.assertIn('error', result)
        self.assertIn('Invalid line', result)

    def test_renderer_output_format_priority_ndjson_over_yaml(self):
        cli = JcCli()
        cli.ndjson_output = True
        cli.yaml_output = True
        cli.mono = True
        cli.data_out = {"key": "val"}
        output = cli.render_output({"key": "val"})
        renderer = cli.create_renderer()
        self.assertEqual(renderer.output_format, OUTPUT_NDJSON)

    def test_render_iter_ndjson_streams_line_by_line(self):
        items = [{"name": "foo"}, {"name": "bar"}, {"name": "baz"}]
        renderer = OutputRenderer(output_format=OUTPUT_NDJSON, mono=True)
        lines = list(renderer.render_iter(iter(items)))
        self.assertEqual(lines, ['{"name":"foo"}', '{"name":"bar"}', '{"name":"baz"}'])

    def test_render_iter_ndjson_empty(self):
        renderer = OutputRenderer(output_format=OUTPUT_NDJSON, mono=True)
        lines = list(renderer.render_iter(iter([])))
        self.assertEqual(lines, [])

    def test_render_iter_ndjson_single_item(self):
        renderer = OutputRenderer(output_format=OUTPUT_NDJSON, mono=True)
        lines = list(renderer.render_iter(iter([{"key": "val"}])))
        self.assertEqual(lines, ['{"key":"val"}'])

    def test_render_iter_json_collects_into_array(self):
        items = [{"name": "foo"}, {"name": "bar"}]
        renderer = OutputRenderer(output_format=OUTPUT_JSON, mono=True)
        lines = list(renderer.render_iter(iter(items)))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], '[{"name":"foo"},{"name":"bar"}]')

    def test_render_iter_json_empty(self):
        renderer = OutputRenderer(output_format=OUTPUT_JSON, mono=True)
        lines = list(renderer.render_iter(iter([])))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], '[]')

    def test_render_iter_json_pretty_collects_into_array(self):
        items = [{"name": "foo"}, {"name": "bar"}]
        renderer = OutputRenderer(output_format=OUTPUT_JSON, pretty=True, mono=True)
        lines = list(renderer.render_iter(iter(items)))
        self.assertEqual(len(lines), 1)
        self.assertIn('"name"', lines[0])
        self.assertIn('"foo"', lines[0])
        self.assertIn('"bar"', lines[0])

    @unittest.skipIf(not RUAMELYAML_INSTALLED, 'ruamel.yaml library not installed')
    def test_render_iter_yaml_collects_into_list(self):
        items = [{"name": "foo"}, {"name": "bar"}]
        renderer = OutputRenderer(output_format=OUTPUT_YAML, mono=True)
        lines = list(renderer.render_iter(iter(items)))
        self.assertEqual(len(lines), 1)
        self.assertIn('name: foo', lines[0])
        self.assertIn('name: bar', lines[0])

    def test_render_iter_ndjson_is_lazy(self):
        consumed = []
        def lazy_items():
            for i in range(3):
                consumed.append(i)
                yield {"i": i}

        renderer = OutputRenderer(output_format=OUTPUT_NDJSON, mono=True)
        gen = renderer.render_iter(lazy_items())
        first = next(gen)
        self.assertEqual(first, '{"i":0}')
        self.assertEqual(len(consumed), 1)
        second = next(gen)
        self.assertEqual(second, '{"i":1}')
        self.assertEqual(len(consumed), 2)

    def test_render_iter_json_is_not_lazy(self):
        consumed = []
        def lazy_items():
            for i in range(3):
                consumed.append(i)
                yield {"i": i}

        renderer = OutputRenderer(output_format=OUTPUT_JSON, mono=True)
        gen = renderer.render_iter(lazy_items())
        first = next(gen)
        self.assertEqual(len(consumed), 3)
        self.assertIn('"i"', first)

    def test_render_iter_json_warn_threshold(self):
        items = [{"i": i} for i in range(5)]
        renderer = OutputRenderer(
            output_format=OUTPUT_JSON,
            mono=True,
            streaming_item_warn=3,
            streaming_item_limit=None,
        )
        import io
        from contextlib import redirect_stderr
        stderr_capture = io.StringIO()
        with redirect_stderr(stderr_capture):
            lines = list(renderer.render_iter(iter(items)))
        self.assertEqual(len(lines), 1)
        stderr_out = stderr_capture.getvalue()
        self.assertIn('collected 4 items', stderr_out)
        self.assertIn('--ndjson-out', stderr_out)

    def test_render_iter_json_no_warn_below_threshold(self):
        items = [{"i": i} for i in range(3)]
        renderer = OutputRenderer(
            output_format=OUTPUT_JSON,
            mono=True,
            streaming_item_warn=10,
            streaming_item_limit=None,
        )
        import io
        from contextlib import redirect_stderr
        stderr_capture = io.StringIO()
        with redirect_stderr(stderr_capture):
            lines = list(renderer.render_iter(iter(items)))
        self.assertEqual(len(lines), 1)
        self.assertEqual(stderr_capture.getvalue(), '')

    def test_render_iter_json_limit_raises_memory_error(self):
        items = [{"i": i} for i in range(5)]
        renderer = OutputRenderer(
            output_format=OUTPUT_JSON,
            mono=True,
            streaming_item_warn=None,
            streaming_item_limit=3,
        )
        with self.assertRaises(MemoryError) as ctx:
            list(renderer.render_iter(iter(items)))
        self.assertIn('exceeding the limit', str(ctx.exception))
        self.assertIn('--ndjson-out', str(ctx.exception))

    def test_render_iter_ndjson_no_warn_regardless_of_threshold(self):
        items = [{"i": i} for i in range(2000)]
        renderer = OutputRenderer(
            output_format=OUTPUT_NDJSON,
            mono=True,
            streaming_item_warn=3,
            streaming_item_limit=5,
        )
        lines = list(renderer.render_iter(iter(items)))
        self.assertEqual(len(lines), 2000)

    def test_render_iter_json_warn_only_once(self):
        items = [{"i": i} for i in range(10)]
        renderer = OutputRenderer(
            output_format=OUTPUT_JSON,
            mono=True,
            streaming_item_warn=3,
            streaming_item_limit=None,
        )
        import io
        from contextlib import redirect_stderr
        stderr_capture = io.StringIO()
        with redirect_stderr(stderr_capture):
            lines = list(renderer.render_iter(iter(items)))
        stderr_out = stderr_capture.getvalue()
        warn_count = stderr_out.count('collected')
        self.assertEqual(warn_count, 1)

    def test_render_iter_json_limit_overrides_warn(self):
        items = [{"i": i} for i in range(10)]
        renderer = OutputRenderer(
            output_format=OUTPUT_JSON,
            mono=True,
            streaming_item_warn=3,
            streaming_item_limit=5,
        )
        with self.assertRaises(MemoryError):
            list(renderer.render_iter(iter(items)))

    def test_streaming_item_warn_default_value(self):
        self.assertEqual(STREAMING_ITEM_WARN_DEFAULT, 1000)

    def test_renderer_default_streaming_item_warn(self):
        renderer = OutputRenderer(output_format=OUTPUT_JSON, mono=True)
        self.assertEqual(renderer._streaming_item_warn, STREAMING_ITEM_WARN_DEFAULT)
        self.assertIsNone(renderer._streaming_item_limit)

    def test_cli_stream_buffer_limit_with_equals(self):
        cli = JcCli()
        cli.args = ['jc', '--csv-s', '--stream-buffer-limit=500']
        cli.options = []
        for opt in cli.args:
            if opt in long_options_map:
                cli.options.extend(long_options_map[opt][0])
            if opt.startswith('--stream-buffer-limit='):
                val = opt.split('=', 1)[1]
                cli.stream_buffer_limit = int(val)
        self.assertEqual(cli.stream_buffer_limit, 500)

    def test_cli_stream_buffer_limit_zero_disables(self):
        cli = JcCli()
        cli.stream_buffer_limit = 0
        cli.mono = True
        renderer = cli.create_renderer()
        self.assertIsNone(renderer._streaming_item_limit)
        self.assertIsNone(renderer._streaming_item_warn)

    def test_cli_stream_buffer_limit_positive_sets_limit(self):
        cli = JcCli()
        cli.stream_buffer_limit = 500
        cli.mono = True
        renderer = cli.create_renderer()
        self.assertEqual(renderer._streaming_item_limit, 500)
        self.assertIsNone(renderer._streaming_item_warn)

    def test_cli_stream_buffer_limit_default_no_limit(self):
        cli = JcCli()
        cli.stream_buffer_limit = None
        cli.mono = True
        renderer = cli.create_renderer()
        self.assertIsNone(renderer._streaming_item_limit)
        self.assertEqual(renderer._streaming_item_warn, STREAMING_ITEM_WARN_DEFAULT)

    def test_cli_stream_buffer_limit_enforced_in_render_iter(self):
        items = [{"i": i} for i in range(10)]
        cli = JcCli()
        cli.stream_buffer_limit = 5
        cli.mono = True
        renderer = cli.create_renderer()
        with self.assertRaises(MemoryError):
            list(renderer.render_iter(iter(items)))

    def test_cli_stream_buffer_limit_zero_no_error(self):
        items = [{"i": i} for i in range(10)]
        cli = JcCli()
        cli.stream_buffer_limit = 0
        cli.mono = True
        renderer = cli.create_renderer()
        lines = list(renderer.render_iter(iter(items)))
        self.assertEqual(len(lines), 1)

if __name__ == '__main__':
    unittest.main()