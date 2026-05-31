#!/usr/bin/env python3
"""
Convert parser doc string to markdown content.

This module provides a pure function that returns markdown content as a string.
File writing is handled exclusively by generate_docs.py.

Usage (deprecated, for debugging only):
    python doc2md.py --stdout jc.parsers.ls   # Print markdown to stdout

For normal use (generate all docs consistently):
    python generate_docs.py             # Generate all docs (including this one)
"""
import sys
import importlib
from pathlib import Path
from inspect import isfunction, signature, cleandoc

PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

_IGNORE_LIB_FUNCTIONS = ['cast', 'wraps', 'lru_cache', 'namedtuple']


def generate_module_doc(mod_path: str) -> str:
    """Return markdown documentation for a module as a string. Does not write to disk."""
    import yapf  # type: ignore

    mod_name = mod_path.split('.')[-1]
    module = importlib.import_module(mod_path)

    header = f'''[Home](https://kellyjonbrazil.github.io/jc/)
<a id="{mod_path}"></a>

# {mod_path}
'''

    summary = module.__doc__ or ''

    functions = []
    for attribute in dir(module):
        if isfunction(getattr(module, attribute)) \
                and not getattr(module, attribute).__name__.startswith('_'):
            if 'jc.parsers.' in mod_path and 'universal' not in mod_path:
                if attribute == 'parse':
                    functions.append(attribute)
            else:
                if attribute not in _IGNORE_LIB_FUNCTIONS:
                    functions.append(attribute)

    toc = f'## Table of Contents\n\n* [{mod_path}](#{mod_path})\n'
    for api in functions:
        toc = f'{toc}  * [{api}](#{mod_path}.{api})\n'

    api_docs = ''
    for api in functions:
        api_function = getattr(module, api)
        this_header = f'<a id="{mod_path}.{api}"></a>\n\n### {api}\n'
        this_sig = str(signature(api_function))
        formatted_sig = yapf.yapf_api.FormatCode(
            f'def {api_function.__name__}{this_sig}:\n    pass'
        )
        formatted_sig = formatted_sig[0].split(':\n    pass')[0]
        this_name_and_sig = f'{this_header}\n```python\n{formatted_sig}\n```'
        this_doc = cleandoc(api_function.__doc__)
        api_docs = api_docs + this_name_and_sig + '\n\n' + this_doc + '\n\n'

    footer = ''
    if 'jc.parsers.' in mod_path and 'universal' not in mod_path:
        footer = '### Parser Information\n'
        comp = ', '.join(module.info.compatible)
        ver = module.info.version
        author = module.info.author
        author_email = module.info.author_email
        slurpable = 'slurpable' in module.info.tags
        footer = footer + f'Compatibility:  {comp}\n\n'
        footer = footer + f'Source: [`jc/parsers/{mod_name}.py`](https://github.com/kellyjonbrazil/jc/blob/master/jc/parsers/{mod_name}.py)\n\n'
        if slurpable:
            footer = footer + 'This parser can be used with the `--slurp` command-line option.\n\n'
        footer = footer + f'Version {ver} by {author} ({author_email})'

    if 'jc.parsers.' in mod_path and 'universal' not in mod_path:
        return header + '\n' + summary + '\n' + api_docs + footer
    elif mod_path == 'jc':
        return header + '\n' + summary
    else:
        return header + '\n' + toc + '\n' + summary + '\n\n' + api_docs


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if a != '--stdout']
    has_stdout = '--stdout' in sys.argv

    if not has_stdout:
        print("=" * 70, file=sys.stderr)
        print("ERROR: This script no longer writes files directly.", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print(file=sys.stderr)
        print("This script has been deprecated in favor of the unified", file=sys.stderr)
        print("documentation generator, which guarantees consistency between", file=sys.stderr)
        print("parser docs, README, man page, and shell completions.", file=sys.stderr)
        print(file=sys.stderr)
        print("Migration guide:", file=sys.stderr)
        print("  OLD: python doc2md.py jc.parsers.ls", file=sys.stderr)
        print("  NEW: python generate_docs.py            (generates all docs)", file=sys.stderr)
        print(file=sys.stderr)
        print("For debugging (print content without writing files):", file=sys.stderr)
        print("  python doc2md.py --stdout jc.parsers.ls", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        sys.exit(1)

    if not args:
        print("Usage: doc2md.py --stdout <module_path>", file=sys.stderr)
        sys.exit(1)

    print(generate_module_doc(args[0]))
