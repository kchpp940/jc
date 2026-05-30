#!/usr/bin/env python3
# Generate README-snap.md from jc release metadata using jinja2 templates
from docgen import jinja_env, release

rel = release()
env = jinja_env()
template = env.get_template('readme-snap_template')
output = template.render(release=rel, snap=rel['snap'])

with open('README-snap.md', 'w') as f:
    f.write(output)
