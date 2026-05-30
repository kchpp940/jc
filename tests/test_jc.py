import unittest
import os
import ast
from ruamel.yaml import YAML
from typing import Generator
import jc

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

def _get_release_from_lib():
    with open(os.path.join(THIS_DIR, os.pardir, 'jc/lib.py'), 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            if node.targets[0].id == '__release__':
                return ast.literal_eval(node.value)
    raise RuntimeError('Could not find __release__ in jc/lib.py')

class MyTests(unittest.TestCase):
    def test_jc_parse_csv(self):
        data = {
            '': [],
            'a,b,c\n1,2,3': [{'a':'1', 'b':'2', 'c':'3'}]
        }

        for test_data, expected_output in data.items():
            self.assertEqual(jc.parse('csv', test_data), expected_output)

    def test_jc_parse_csv_s_is_generator(self):
        self.assertIsInstance(jc.parse('csv_s', 'a,b,c\n1,2,3'), Generator)

    def test_jc_parse_kv(self):
        data = {
            '': {},
            'a=1\nb=2\nc=3': {'a':'1', 'b':'2', 'c':'3'}
        }

        for test_data, expected_output in data.items():
            self.assertEqual(jc.parse('kv', test_data), expected_output)

    def test_jc_parser_mod_list_is_list(self):
        self.assertIsInstance(jc.parser_mod_list(), list)

    def test_jc_parser_mod_list_contains_csv(self):
        self.assertTrue('csv' in jc.parser_mod_list())

    def test_jc_parser_mod_list_length(self):
        self.assertGreaterEqual(len(jc.parser_mod_list()), 80)

    def test_jc_plugin_parser_mod_list_is_list(self):
        self.assertIsInstance(jc.plugin_parser_mod_list(), list)

    def test_jc_slurpable_parser_mod_list_is_list(self):
        self.assertIsInstance(jc.slurpable_parser_mod_list(), list)

    def test_version_info(self):
        """Test that __version__ and __release__ are consistent and setup.py reads from lib.py."""
        release = _get_release_from_lib()

        self.assertEqual(jc.__version__, release['version'],
                         '__version__ must equal __release__[\"version\"]')
        self.assertEqual(jc.__release__['version'], release['version'])

        with open(os.path.join(THIS_DIR, os.pardir, 'setup.py'), 'r', encoding='utf-8') as f:
            setup_file = f.read()

        self.assertIn('_get_release()', setup_file,
                       'setup.py should use _get_release() from jc/lib.py')
        self.assertIn("open('jc/lib.py'", setup_file)

    def test_release_metadata_keys(self):
        """Test that __release__ contains all required release metadata keys."""
        release = _get_release_from_lib()
        required_keys = [
            'version', 'name', 'description', 'author', 'author_email',
            'website', 'license', 'copyright', 'python_requires',
            'install_requires', 'snap',
        ]
        for key in required_keys:
            self.assertIn(key, release, f'__release__ missing required key: {key}')

    def test_release_snap_keys(self):
        """Test that __release__['snap'] contains all required snap metadata keys."""
        release = _get_release_from_lib()
        snap_required = ['base', 'confinement', 'grade', 'branch']
        for key in snap_required:
            self.assertIn(key, release['snap'],
                          f'__release__[\"snap\"] missing required key: {key}')

    def test_setup_deps_match_release(self):
        """Test that setup.py install_requires is sourced from __release__ via _get_release()."""
        with open(os.path.join(THIS_DIR, os.pardir, 'setup.py'), 'r', encoding='utf-8') as f:
            setup_file = f.read()

        self.assertIn("release['install_requires']", setup_file,
                       'setup.py should pass release[\"install_requires\"] to setuptools')
        self.assertNotIn('ruamel.yaml', setup_file,
                         'setup.py should not hardcode dependency names; read from __release__ instead')

    def test_snapcraft_reads_release(self):
        """Test that snapcraft.yaml override-pull reads from jc/lib.py __release__."""
        with open(os.path.join(THIS_DIR, os.pardir, 'snap/snapcraft.yaml'), 'r', encoding='utf-8') as f:
            snap_file = f.read()

        self.assertIn('jc/lib.py', snap_file,
                       'snapcraft.yaml should reference jc/lib.py')
        self.assertIn('__release__', snap_file,
                       'snapcraft.yaml should reference __release__')

    def test_snapcraft_fields_match_release(self):
        """Test that snapcraft.yaml hardcoded fields match __release__['snap']."""
        release = _get_release_from_lib()
        yaml = YAML(typ='safe')
        with open(os.path.join(THIS_DIR, os.pardir, 'snap/snapcraft.yaml'), 'r', encoding='utf-8') as f:
            snap = yaml.load(f)

        self.assertEqual(snap['base'], release['snap']['base'])
        self.assertEqual(snap['confinement'], release['snap']['confinement'])
        self.assertEqual(snap['license'], release['license'])
        self.assertEqual(snap['website'], release['website'])
        self.assertEqual(snap['source-code'], release['website'])
        self.assertEqual(snap['contact'], f"{release['author']} <{release['author_email']}>")

if __name__ == '__main__':
    unittest.main()