import unittest
import os
import sys
import shutil
import tempfile
import importlib
from unittest.mock import patch

import jc.appdirs as _appdirs
from jc.registry import ParserRegistry, cliname_to_modname, modname_to_cliname


def _make_plugin(jcparsers_dir, filename, content):
    with open(os.path.join(jcparsers_dir, filename), 'w') as f:
        f.write(content)


class _Fixture:
    """Helper that creates a temp data_dir with jcparsers/ and
    disabled_parsers.txt, patches appdirs, and yields the paths.
    On teardown also cleans sys.path and sys.modules to avoid
    leaking plugin modules into other tests."""

    def __init__(self):
        self.tmpdir = None
        self.jcparsers_dir = None
        self.disabled_file = None
        self._pre_sys_path = None
        self._pre_sys_modules_keys = None

    def setup(self):
        self.tmpdir = tempfile.mkdtemp()
        self.jcparsers_dir = os.path.join(self.tmpdir, 'jcparsers')
        os.makedirs(self.jcparsers_dir)
        self.disabled_file = os.path.join(self.tmpdir, 'disabled_parsers.txt')
        self._pre_sys_path = list(sys.path)
        self._pre_sys_modules_keys = set(sys.modules.keys())

    def teardown(self):
        if self.tmpdir and os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir)
        sys.path[:] = self._pre_sys_path
        for key in list(sys.modules.keys()):
            if key not in self._pre_sys_modules_keys:
                if key.startswith('jcparsers'):
                    del sys.modules[key]


def _new_registry(data_dir):
    """Build a fresh ParserRegistry pointing at *data_dir*."""
    with patch.object(_appdirs, 'user_data_dir', return_value=data_dir):
        reg = ParserRegistry()
    return reg


# ── name conversion ────────────────────────────────────────────────────

class TestNameConversion(unittest.TestCase):

    def test_cliname_to_modname_dash(self):
        self.assertEqual(cliname_to_modname('my-parser'), 'my_parser')

    def test_cliname_to_modname_double_dash_prefix(self):
        self.assertEqual(cliname_to_modname('--my-parser'), 'my_parser')

    def test_modname_to_cliname(self):
        self.assertEqual(modname_to_cliname('my_parser'), 'my-parser')


# ── no plugins present ─────────────────────────────────────────────────

class TestNoPlugins(unittest.TestCase):

    def setUp(self):
        self.fix = _Fixture()
        self.fix.setup()
        self.reg = _new_registry(self.fix.tmpdir)

    def tearDown(self):
        self.fix.teardown()

    def test_parsers_contains_builtins(self):
        self.assertIn('date', self.reg.parsers)
        self.assertIn('csv', self.reg.parsers)

    def test_plugin_parsers_empty(self):
        self.assertEqual(self.reg.plugin_parsers, [])

    def test_disabled_parsers_empty(self):
        self.assertEqual(self.reg.disabled_parsers, set())

    def test_overridden_parsers_empty(self):
        self.assertEqual(self.reg.overridden_parsers, set())

    def test_broken_parsers_empty(self):
        self.assertEqual(self.reg.broken_parsers, set())

    def test_is_plugin_false_for_builtin(self):
        self.assertFalse(self.reg.is_plugin('date'))

    def test_is_overridden_false(self):
        self.assertFalse(self.reg.is_overridden('date'))

    def test_is_disabled_false(self):
        self.assertFalse(self.reg.is_disabled('date'))

    def test_is_broken_false(self):
        self.assertFalse(self.reg.is_broken('date'))


# ── valid new plugin ───────────────────────────────────────────────────

class TestValidNewPlugin(unittest.TestCase):

    def setUp(self):
        self.fix = _Fixture()
        self.fix.setup()
        _make_plugin(self.fix.jcparsers_dir, 'mycustom.py',
            "info = type('info', (), {'description': 'custom', 'author': 'me', "
            "'version': '0.1', 'compatible': ['linux'], 'tags': [], "
            "'magic_commands': []})()\n"
            "def parse(data, raw=False, quiet=False, **kwargs):\n"
            "    return {'custom': True}\n")
        self.reg = _new_registry(self.fix.tmpdir)

    def tearDown(self):
        self.fix.teardown()

    def test_plugin_discovered(self):
        self.assertIn('mycustom', self.reg.plugin_parsers)

    def test_plugin_in_parsers(self):
        self.assertIn('mycustom', self.reg.parsers)

    def test_is_plugin_true(self):
        self.assertTrue(self.reg.is_plugin('mycustom'))

    def test_module_cached(self):
        mod = self.reg.get_cached_module('mycustom')
        self.assertIsNotNone(mod)
        self.assertTrue(hasattr(mod, 'parse'))


# ── broken plugin (missing parse) ──────────────────────────────────────

class TestBrokenPlugin(unittest.TestCase):

    def setUp(self):
        self.fix = _Fixture()
        self.fix.setup()
        _make_plugin(self.fix.jcparsers_dir, 'broken.py',
            "info = type('info', (), {})()\n")
        self.reg = _new_registry(self.fix.tmpdir)

    def tearDown(self):
        self.fix.teardown()

    def test_not_in_plugin_parsers(self):
        self.assertNotIn('broken', self.reg.plugin_parsers)

    def test_not_in_parsers(self):
        self.assertNotIn('broken', self.reg.parsers)

    def test_in_broken_parsers(self):
        self.assertIn('broken', self.reg.broken_parsers)

    def test_in_disabled_parsers(self):
        self.assertIn('broken', self.reg.disabled_parsers)

    def test_is_broken_true(self):
        self.assertTrue(self.reg.is_broken('broken'))

    def test_is_disabled_true(self):
        self.assertTrue(self.reg.is_disabled('broken'))

    def test_no_module_cached(self):
        self.assertIsNone(self.reg.get_cached_module('broken'))


# ── broken plugin (import error) ───────────────────────────────────────

class TestBrokenPluginImportError(unittest.TestCase):

    def setUp(self):
        self.fix = _Fixture()
        self.fix.setup()
        _make_plugin(self.fix.jcparsers_dir, 'bad_import.py',
            "raise RuntimeError('cannot import')\n")
        self.reg = _new_registry(self.fix.tmpdir)

    def tearDown(self):
        self.fix.teardown()

    def test_in_broken_parsers(self):
        self.assertIn('bad-import', self.reg.broken_parsers)

    def test_in_disabled_parsers(self):
        self.assertIn('bad-import', self.reg.disabled_parsers)

    def test_not_in_parsers(self):
        self.assertNotIn('bad-import', self.reg.parsers)


# ── override builtin parser ────────────────────────────────────────────

class TestOverrideBuiltin(unittest.TestCase):

    def setUp(self):
        self.fix = _Fixture()
        self.fix.setup()
        _make_plugin(self.fix.jcparsers_dir, 'date.py',
            "import jc.parsers.date as _builtin\n"
            "info = _builtin.info\n"
            "def parse(data, raw=False, quiet=False, **kwargs):\n"
            "    return _builtin.parse(data, raw=raw, quiet=quiet, **kwargs)\n")
        self.reg = _new_registry(self.fix.tmpdir)

    def tearDown(self):
        self.fix.teardown()

    def test_date_in_plugin_parsers(self):
        self.assertIn('date', self.reg.plugin_parsers)

    def test_date_in_overridden_parsers(self):
        self.assertIn('date', self.reg.overridden_parsers)

    def test_is_overridden_true(self):
        self.assertTrue(self.reg.is_overridden('date'))

    def test_is_plugin_true(self):
        self.assertTrue(self.reg.is_plugin('date'))

    def test_date_still_in_parsers(self):
        self.assertIn('date', self.reg.parsers)

    def test_module_cached(self):
        mod = self.reg.get_cached_module('date')
        self.assertIsNotNone(mod)


# ── user-disabled plugin ───────────────────────────────────────────────

class TestUserDisabledPlugin(unittest.TestCase):

    def setUp(self):
        self.fix = _Fixture()
        self.fix.setup()
        _make_plugin(self.fix.jcparsers_dir, 'mycustom.py',
            "info = type('info', (), {'description': 'custom', 'author': 'me', "
            "'version': '0.1', 'compatible': ['linux'], 'tags': [], "
            "'magic_commands': []})()\n"
            "def parse(data, raw=False, quiet=False, **kwargs):\n"
            "    return {'custom': True}\n")
        with open(self.fix.disabled_file, 'w') as f:
            f.write('mycustom\n# a comment\n')
        self.reg = _new_registry(self.fix.tmpdir)

    def tearDown(self):
        self.fix.teardown()

    def test_not_in_plugin_parsers(self):
        self.assertNotIn('mycustom', self.reg.plugin_parsers)

    def test_not_in_parsers(self):
        self.assertNotIn('mycustom', self.reg.parsers)

    def test_in_disabled_parsers(self):
        self.assertIn('mycustom', self.reg.disabled_parsers)

    def test_in_user_disabled_parsers(self):
        self.assertIn('mycustom', self.reg.user_disabled_parsers)

    def test_is_user_disabled_true(self):
        self.assertTrue(self.reg.is_user_disabled('mycustom'))

    def test_is_disabled_true(self):
        self.assertTrue(self.reg.is_disabled('mycustom'))

    def test_is_broken_false(self):
        self.assertFalse(self.reg.is_broken('mycustom'))

    def test_no_module_cached(self):
        self.assertIsNone(self.reg.get_cached_module('mycustom'))


# ── user-disabled with --prefix and underscore ─────────────────────────

class TestUserDisabledNameNormalization(unittest.TestCase):

    def setUp(self):
        self.fix = _Fixture()
        self.fix.setup()
        _make_plugin(self.fix.jcparsers_dir, 'my_custom.py',
            "info = type('info', (), {'description': 'custom', 'author': 'me', "
            "'version': '0.1', 'compatible': ['linux'], 'tags': [], "
            "'magic_commands': []})()\n"
            "def parse(data, raw=False, quiet=False, **kwargs):\n"
            "    return {'custom': True}\n")
        with open(self.fix.disabled_file, 'w') as f:
            f.write('--my-custom\n')
        self.reg = _new_registry(self.fix.tmpdir)

    def tearDown(self):
        self.fix.teardown()

    def test_normalizes_dashes_and_prefix(self):
        self.assertIn('my-custom', self.reg.user_disabled_parsers)

    def test_is_user_disabled(self):
        self.assertTrue(self.reg.is_user_disabled('my-custom'))


# ── user-disabled override (disabled takes priority) ───────────────────

class TestUserDisabledOverride(unittest.TestCase):

    def setUp(self):
        self.fix = _Fixture()
        self.fix.setup()
        _make_plugin(self.fix.jcparsers_dir, 'date.py',
            "import jc.parsers.date as _builtin\n"
            "info = _builtin.info\n"
            "def parse(data, raw=False, quiet=False, **kwargs):\n"
            "    return _builtin.parse(data, raw=raw, quiet=quiet, **kwargs)\n")
        with open(self.fix.disabled_file, 'w') as f:
            f.write('date\n')
        self.reg = _new_registry(self.fix.tmpdir)

    def tearDown(self):
        self.fix.teardown()

    def test_not_in_overridden(self):
        self.assertNotIn('date', self.reg.overridden_parsers)

    def test_in_disabled(self):
        self.assertIn('date', self.reg.disabled_parsers)

    def test_not_in_plugin_parsers(self):
        self.assertNotIn('date', self.reg.plugin_parsers)


# ── disabled_parsers.txt with comments and blank lines ─────────────────

class TestDisabledFileFormat(unittest.TestCase):

    def setUp(self):
        self.fix = _Fixture()
        self.fix.setup()
        _make_plugin(self.fix.jcparsers_dir, 'mycustom.py',
            "info = type('info', (), {'description': 'custom', 'author': 'me', "
            "'version': '0.1', 'compatible': ['linux'], 'tags': [], "
            "'magic_commands': []})()\n"
            "def parse(data, raw=False, quiet=False, **kwargs):\n"
            "    return {'custom': True}\n")
        with open(self.fix.disabled_file, 'w') as f:
            f.write('\n# comment\nmycustom\n\n')
        self.reg = _new_registry(self.fix.tmpdir)

    def tearDown(self):
        self.fix.teardown()

    def test_only_nonempty_noncomment_lines_counted(self):
        self.assertEqual(self.reg.user_disabled_parsers, {'mycustom'})


# ── no disabled_parsers.txt file ───────────────────────────────────────

class TestNoDisabledFile(unittest.TestCase):

    def setUp(self):
        self.fix = _Fixture()
        self.fix.setup()
        self.reg = _new_registry(self.fix.tmpdir)

    def tearDown(self):
        self.fix.teardown()

    def test_user_disabled_empty(self):
        self.assertEqual(self.reg.user_disabled_parsers, set())


# ── non-*.py files ignored ─────────────────────────────────────────────

class TestNonPyFilesIgnored(unittest.TestCase):

    def setUp(self):
        self.fix = _Fixture()
        self.fix.setup()
        with open(os.path.join(self.fix.jcparsers_dir, 'README.md'), 'w') as f:
            f.write('not a plugin')
        with open(os.path.join(self.fix.jcparsers_dir, '__init__.py'), 'w') as f:
            f.write('')
        self.reg = _new_registry(self.fix.tmpdir)

    def tearDown(self):
        self.fix.teardown()

    def test_no_plugins_discovered(self):
        self.assertEqual(self.reg.plugin_parsers, [])


# ── mark_disabled at runtime ───────────────────────────────────────────

class TestMarkDisabledRuntime(unittest.TestCase):

    def setUp(self):
        self.fix = _Fixture()
        self.fix.setup()
        self.reg = _new_registry(self.fix.tmpdir)

    def tearDown(self):
        self.fix.teardown()

    def test_mark_disabled_adds_to_set(self):
        self.reg.mark_disabled('some-parser')
        self.assertIn('some-parser', self.reg.disabled_parsers)
        self.assertTrue(self.reg.is_disabled('some-parser'))

    def test_mark_disabled_idempotent(self):
        self.reg.mark_disabled('some-parser')
        self.reg.mark_disabled('some-parser')
        self.assertEqual(len([p for p in self.reg.disabled_parsers if p == 'some-parser']), 1)


# ── cache_module and get_cached_module ─────────────────────────────────

class TestModuleCache(unittest.TestCase):

    def setUp(self):
        self.fix = _Fixture()
        self.fix.setup()
        self.reg = _new_registry(self.fix.tmpdir)

    def tearDown(self):
        self.fix.teardown()

    def test_cache_roundtrip(self):
        import types
        mod = types.ModuleType('test_mod')
        self.reg.cache_module('test-mod', mod)
        self.assertIs(self.reg.get_cached_module('test-mod'), mod)

    def test_missing_returns_none(self):
        self.assertIsNone(self.reg.get_cached_module('nonexistent'))


# ── parser_info integration ────────────────────────────────────────────

class TestParserInfoIntegration(unittest.TestCase):

    def setUp(self):
        self.fix = _Fixture()
        self.fix.setup()
        _make_plugin(self.fix.jcparsers_dir, 'mycustom.py',
            "info = type('info', (), {'description': 'custom', 'author': 'me', "
            "'version': '0.1', 'compatible': ['linux'], 'tags': [], "
            "'magic_commands': []})()\n"
            "def parse(data, raw=False, quiet=False, **kwargs):\n"
            "    return {'custom': True}\n")
        _make_plugin(self.fix.jcparsers_dir, 'date.py',
            "import jc.parsers.date as _builtin\n"
            "info = _builtin.info\n"
            "def parse(data, raw=False, quiet=False, **kwargs):\n"
            "    return _builtin.parse(data, raw=raw, quiet=quiet, **kwargs)\n")
        _make_plugin(self.fix.jcparsers_dir, 'broken.py',
            "info = type('info', (), {})()\n")
        with open(self.fix.disabled_file, 'w') as f:
            f.write('mycustom\n')
        self.reg = _new_registry(self.fix.tmpdir)
        import jc.lib
        self._orig_registry = jc.lib.registry
        self._orig_parsers = jc.lib.parsers
        self._orig_local = jc.lib.local_parsers
        jc.lib.registry = self.reg
        jc.lib.parsers = self.reg.parsers
        jc.lib.local_parsers = self.reg.plugin_parsers

    def tearDown(self):
        import jc.lib
        jc.lib.registry = self._orig_registry
        jc.lib.parsers = self._orig_parsers
        jc.lib.local_parsers = self._orig_local
        self.fix.teardown()

    def test_builtin_parser_info_no_plugin_flag(self):
        import jc.lib
        info = jc.lib.parser_info('csv')
        self.assertNotIn('plugin', info)
        self.assertNotIn('overrides_builtin', info)
        self.assertNotIn('disabled', info)
        self.assertNotIn('broken', info)

    def test_override_parser_info_has_flags(self):
        import jc.lib
        info = jc.lib.parser_info('date')
        self.assertTrue(info.get('plugin'))
        self.assertTrue(info.get('overrides_builtin'))

    def test_user_disabled_not_in_parsers_list(self):
        import jc.lib
        self.assertNotIn('mycustom', jc.lib.parsers)

    def test_user_disabled_get_parser_returns_disabled_module(self):
        import jc.lib
        mod = jc.lib.get_parser('mycustom')
        self.assertEqual(mod.__name__, 'mycustom')


# ── about_jc integration ───────────────────────────────────────────────

class TestAboutJcIntegration(unittest.TestCase):

    def setUp(self):
        self.fix = _Fixture()
        self.fix.setup()
        _make_plugin(self.fix.jcparsers_dir, 'mycustom.py',
            "info = type('info', (), {'description': 'custom', 'author': 'me', "
            "'version': '0.1', 'compatible': ['linux'], 'tags': [], "
            "'magic_commands': []})()\n"
            "def parse(data, raw=False, quiet=False, **kwargs):\n"
            "    return {'custom': True}\n")
        _make_plugin(self.fix.jcparsers_dir, 'date.py',
            "import jc.parsers.date as _builtin\n"
            "info = _builtin.info\n"
            "def parse(data, raw=False, quiet=False, **kwargs):\n"
            "    return _builtin.parse(data, raw=raw, quiet=quiet, **kwargs)\n")
        _make_plugin(self.fix.jcparsers_dir, 'broken.py',
            "info = type('info', (), {})()\n")
        with open(self.fix.disabled_file, 'w') as f:
            f.write('mycustom\n')
        self.reg = _new_registry(self.fix.tmpdir)
        import jc.lib, jc.cli
        self._saved = {
            'lib_reg': jc.lib.registry,
            'lib_parsers': jc.lib.parsers,
            'lib_local': jc.lib.local_parsers,
            'cli_reg': jc.cli.registry,
        }
        jc.lib.registry = self.reg
        jc.lib.parsers = self.reg.parsers
        jc.lib.local_parsers = self.reg.plugin_parsers
        jc.cli.registry = self.reg

    def tearDown(self):
        import jc.lib, jc.cli
        jc.lib.registry = self._saved['lib_reg']
        jc.lib.parsers = self._saved['lib_parsers']
        jc.lib.local_parsers = self._saved['lib_local']
        jc.cli.registry = self._saved['cli_reg']
        self.fix.teardown()

    def test_about_counts_reflect_registry(self):
        from jc.cli import JcCli
        about = JcCli.about_jc()
        self.assertGreaterEqual(about['disabled_parser_count'], 2)
        self.assertGreaterEqual(about['broken_parser_count'], 1)
        self.assertGreaterEqual(about['overridden_parser_count'], 1)
        self.assertIn('date', about.get('overridden_parsers', []))
        self.assertIn('broken', about.get('broken_parsers', []))
        self.assertIn('mycustom', about.get('disabled_parsers', []))


# ── shell completion excludes disabled plugins ─────────────────────────

class TestShellCompletionExcludesDisabled(unittest.TestCase):

    def setUp(self):
        self.fix = _Fixture()
        self.fix.setup()
        _make_plugin(self.fix.jcparsers_dir, 'mycustom.py',
            "info = type('info', (), {'description': 'custom', 'author': 'me', "
            "'version': '0.1', 'compatible': ['linux'], 'tags': [], "
            "'magic_commands': []})()\n"
            "def parse(data, raw=False, quiet=False, **kwargs):\n"
            "    return {'custom': True}\n")
        _make_plugin(self.fix.jcparsers_dir, 'disabled_plugin.py',
            "info = type('info', (), {'description': 'disabled one', 'author': 'me', "
            "'version': '0.1', 'compatible': ['linux'], 'tags': [], "
            "'magic_commands': []})()\n"
            "def parse(data, raw=False, quiet=False, **kwargs):\n"
            "    return {'disabled': True}\n")
        with open(self.fix.disabled_file, 'w') as f:
            f.write('disabled-plugin\n')
        self.reg = _new_registry(self.fix.tmpdir)

    def tearDown(self):
        self.fix.teardown()

    def test_disabled_plugin_not_in_parsers(self):
        self.assertNotIn('disabled-plugin', self.reg.parsers)

    def test_active_plugin_in_parsers(self):
        self.assertIn('mycustom', self.reg.parsers)

    def test_disabled_plugin_in_disabled_set(self):
        self.assertIn('disabled-plugin', self.reg.disabled_parsers)


# ── multiple plugins: mix of states ────────────────────────────────────

class TestMixedPluginStates(unittest.TestCase):

    def setUp(self):
        self.fix = _Fixture()
        self.fix.setup()
        _make_plugin(self.fix.jcparsers_dir, 'good.py',
            "info = type('info', (), {'description': 'good', 'author': 'me', "
            "'version': '0.1', 'compatible': ['linux'], 'tags': [], "
            "'magic_commands': []})()\n"
            "def parse(data, raw=False, quiet=False, **kwargs):\n"
            "    return {'good': True}\n")
        _make_plugin(self.fix.jcparsers_dir, 'broken.py',
            "info = type('info', (), {})()\n")
        _make_plugin(self.fix.jcparsers_dir, 'date.py',
            "import jc.parsers.date as _builtin\n"
            "info = _builtin.info\n"
            "def parse(data, raw=False, quiet=False, **kwargs):\n"
            "    return _builtin.parse(data, raw=raw, quiet=quiet, **kwargs)\n")
        _make_plugin(self.fix.jcparsers_dir, 'userdisabled.py',
            "info = type('info', (), {'description': 'ud', 'author': 'me', "
            "'version': '0.1', 'compatible': ['linux'], 'tags': [], "
            "'magic_commands': []})()\n"
            "def parse(data, raw=False, quiet=False, **kwargs):\n"
            "    return {'ud': True}\n")
        with open(self.fix.disabled_file, 'w') as f:
            f.write('userdisabled\n')
        self.reg = _new_registry(self.fix.tmpdir)

    def tearDown(self):
        self.fix.teardown()

    def test_good_plugin_discovered(self):
        self.assertIn('good', self.reg.plugin_parsers)
        self.assertFalse(self.reg.is_disabled('good'))
        self.assertFalse(self.reg.is_broken('good'))

    def test_broken_plugin_marked(self):
        self.assertIn('broken', self.reg.broken_parsers)
        self.assertIn('broken', self.reg.disabled_parsers)
        self.assertNotIn('broken', self.reg.plugin_parsers)

    def test_override_detected(self):
        self.assertIn('date', self.reg.overridden_parsers)
        self.assertTrue(self.reg.is_overridden('date'))
        self.assertTrue(self.reg.is_plugin('date'))

    def test_user_disabled(self):
        self.assertIn('userdisabled', self.reg.disabled_parsers)
        self.assertIn('userdisabled', self.reg.user_disabled_parsers)
        self.assertNotIn('userdisabled', self.reg.plugin_parsers)

    def test_disabled_superset(self):
        self.assertTrue(self.reg.disabled_parsers >= self.reg.broken_parsers)
        self.assertTrue(self.reg.disabled_parsers >= self.reg.user_disabled_parsers)


if __name__ == '__main__':
    unittest.main()
