#!/usr/bin/env python3
# Generate README.md from jc metadata using jinja2 templates
import jc.metadata
from jinja2 import Environment, FileSystemLoader

file_loader = FileSystemLoader('templates')
env = Environment(loader=file_loader)
template = env.get_template('readme_template')
output = template.render(parsers=jc.metadata.all_parser_info(),
                         info=jc.metadata.jc_about())

with open('README.md', 'w') as f:
    f.write(output)
