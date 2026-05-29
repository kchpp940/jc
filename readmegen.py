#!/usr/bin/env python3
# Generate README.md from jc metadata using jinja2 templates
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = SCRIPT_DIR
sys.path.insert(0, PROJECT_ROOT)

import jc.cli
from jc.metadata_policy import for_readme
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = os.path.join(PROJECT_ROOT, 'templates')
OUTPUT_FILE = os.path.join(PROJECT_ROOT, 'README.md')

file_loader = FileSystemLoader(TEMPLATES_DIR)
env = Environment(loader=file_loader)
template = env.get_template('readme_template')
output = template.render(parsers=for_readme(),
                         info=jc.cli.JcCli.about_jc())

with open(OUTPUT_FILE, 'w') as f:
    f.write(output)
