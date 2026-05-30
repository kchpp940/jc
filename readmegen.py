#!/usr/bin/env python3
# Generate README.md from jc metadata using jinja2 templates
from _docgen import get_jinja_env, get_parsers, get_jc_info, write_output, PROJECT_ROOT

env = get_jinja_env()
template = env.get_template('readme_template')
output = template.render(parsers=get_parsers(), info=get_jc_info())

write_output(PROJECT_ROOT / 'README.md', output)
