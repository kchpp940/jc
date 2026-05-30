#!/usr/bin/env python3

"""
Convert parser doc string to markdown
"""
import sys
import importlib
from inspect import isfunction, signature, cleandoc
import textwrap

ignore_lib_functions = [
    'cast',
    'wraps',
    'lru_cache',
    'namedtuple'
]


def _format_signature(name: str, sig: str) -> str:
    """
    Format a function signature using yapf if available.
    Falls back to the raw signature string if yapf is not installed.
    """
    try:
        import yapf  # type: ignore
        formatted = yapf.yapf_api.FormatCode(f'def {name}{sig}:\n    pass')
        return formatted[0].split(':\n    pass')[0]
    except ImportError:
        return f'def {name}{sig}'

mod_path = sys.argv[1]
mod_name = mod_path.split('.')[-1]
module = importlib.import_module(f'{mod_path}')

_JC_META_REF = '# _jc_meta schema: see jc.streaming._JC_META_PROGRESS_SCHEMA'


def expand_jc_meta_schema(doc: str) -> str:
    """
    Expand the _jc_meta schema reference inline in docstrings.
    Replaces the reference line with the actual schema from
    jc.streaming._JC_META_PROGRESS_SCHEMA so that generated
    documentation shows the full field descriptions.
    """
    lines = doc.split('\n')
    found = False
    for i, line in enumerate(lines):
        if _JC_META_REF in line:
            found = True
            import jc.streaming
            schema = jc.streaming._JC_META_PROGRESS_SCHEMA
            dedented_schema = textwrap.dedent(schema).strip('\n')
            base_indent = len(line) - len(line.lstrip())
            indented_schema = '\n'.join(
                ' ' * base_indent + s if s else s
                for s in dedented_schema.split('\n')
            )
            lines[i] = indented_schema
            break
    if not found:
        return doc
    return '\n'.join(lines)

######## HEADER ########
header = f'''[Home](https://kellyjonbrazil.github.io/jc/)
<a id="{mod_path}"></a>

# {mod_path}
'''

summary = expand_jc_meta_schema(module.__doc__ or '')

functions = []
for attribute in dir(module):
    if isfunction(getattr(module, attribute)) \
        and not getattr(module, attribute).__name__.startswith('_'):

        if 'jc.parsers.' in mod_path and not 'universal' in mod_path:
            if attribute == 'parse':
                functions.append(attribute)

        else:
            if not attribute in ignore_lib_functions:
                functions.append(attribute)

######## TABLE OF CONTENTS ########
toc = f'## Table of Contents\n\n* [{mod_path}](#{mod_path})\n'
for api in functions:
    toc = f'{toc}  * [{api}](#{mod_path}.{api})\n'

######## API DOCS ########
api_docs = ''
for api in functions:
    api_function = getattr(module, api)

    this_header = f'<a id="{mod_path}.{api}"></a>\n\n### {api}\n'
    this_sig = str(signature(api_function))
    formatted_sig = _format_signature(api_function.__name__, this_sig)
    this_name_and_sig = f'{this_header}\n```python\n{formatted_sig}\n```'

    this_doc = cleandoc(api_function.__doc__)
    this_doc = expand_jc_meta_schema(this_doc)
    api_docs = api_docs + this_name_and_sig + '\n\n' + this_doc + '\n\n'

######## FOOTER ########
footer = ''
if 'jc.parsers.' in mod_path and not 'universal' in mod_path:
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

final_doc = ''
if 'jc.parsers.' in mod_path and not 'universal' in mod_path:
    final_doc = header + '\n' + summary + '\n' + api_docs + footer
elif mod_path == 'jc':
    final_doc = header + '\n' + summary
else:
    final_doc = header + '\n' + toc + '\n' + summary + '\n\n' + api_docs

print(final_doc)
