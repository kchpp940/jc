#!/usr/bin/env python3
# Generate man page from jc metadata using jinja2 templates
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = SCRIPT_DIR
sys.path.insert(0, PROJECT_ROOT)

from datetime import date
import jc.cli
from jc.metadata_policy import for_man_page
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = os.path.join(PROJECT_ROOT, 'templates')
OUTPUT_FILE = os.path.join(PROJECT_ROOT, 'man', 'jc.1')

file_loader = FileSystemLoader(TEMPLATES_DIR)
env = Environment(loader=file_loader)
template = env.get_template('manpage_template')

about_jc = jc.cli.JcCli.about_jc()
about_jc['parsers'] = for_man_page()

output = template.render(today=date.today(),
                         jc=about_jc)

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
with open(OUTPUT_FILE, 'w') as f:
    f.write(output)
