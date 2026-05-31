#!/usr/bin/env python3
# Generate man page from jc metadata using jinja2 templates
import sys
from datetime import date
import jc.cli
from jinja2 import Environment, FileSystemLoader


def generate_manpage() -> str:
    """Generate man page content and return as string."""
    file_loader = FileSystemLoader('templates')
    env = Environment(loader=file_loader)
    template = env.get_template('manpage_template')
    output = template.render(today=date.today(),
                             jc=jc.cli.JcCli.about_jc())
    return output


if __name__ == '__main__':
    content = generate_manpage()

    if '--stdout' in sys.argv:
        sys.stdout.write(content)
        sys.stdout.flush()
    else:
        with open('man/jc.1', 'w') as f:
            f.write(content)
