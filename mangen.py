#!/usr/bin/env python3
# Generate man page from jc metadata using jinja2 templates
from datetime import date
import jc.cli
from docgen import jinja_env

env = jinja_env()
template = env.get_template('manpage_template')
output = template.render(today=date.today(),
                         jc=jc.cli.JcCli.about_jc())

with open('man/jc.1', 'w') as f:
    f.write(output)
