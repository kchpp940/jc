#!/usr/bin/env python3
# Generate README.md from jc metadata using jinja2 templates
import jc.cli
import jc.lib
from jc.docrules import is_doc_complete
from jinja2 import Environment, FileSystemLoader


parsers_info = jc.lib.all_parser_info()
for p in parsers_info:
    p['doc_complete'] = is_doc_complete(p)

file_loader = FileSystemLoader('templates')
env = Environment(loader=file_loader)
template = env.get_template('readme_template')
output = template.render(parsers=parsers_info,
                         info=jc.cli.JcCli.about_jc())

with open('README.md', 'w') as f:
    f.write(output)
