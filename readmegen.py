#!/usr/bin/env python3
# Generate README.md from jc metadata using jinja2 templates
import jc.cli
import jc.lib
from docgen import jinja_env

env = jinja_env()
template = env.get_template('readme_template')
output = template.render(parsers=jc.lib.all_parser_info(),
                         info=jc.cli.JcCli.about_jc())

with open('README.md', 'w') as f:
    f.write(output)
