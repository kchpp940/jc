#!/usr/bin/env python3
# Generate man page from jc metadata using jinja2 templates
from datetime import date
from _docgen import get_jinja_env, get_jc_info, write_output, MAN_DIR

env = get_jinja_env()
template = env.get_template('manpage_template')
output = template.render(today=date.today(), jc=get_jc_info())

write_output(MAN_DIR / 'jc.1', output)
