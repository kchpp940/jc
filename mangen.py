#!/usr/bin/env python3
# Generate man page from jc metadata using jinja2 templates
from datetime import date
import jc.cli
from jc.docrules import is_doc_complete
from jinja2 import Environment, FileSystemLoader


about_info = jc.cli.JcCli.about_jc()
for p in about_info['parsers']:
    p['doc_complete'] = is_doc_complete(p)

file_loader = FileSystemLoader('templates')
env = Environment(loader=file_loader)
template = env.get_template('manpage_template')
output = template.render(today=date.today(),
                         jc=about_info)

with open('man/jc.1', 'w') as f:
    f.write(output)
