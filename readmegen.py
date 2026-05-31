#!/usr/bin/env python3
# Generate README.md from jc metadata using jinja2 templates
import sys
import jc.cli
import jc.lib
from jinja2 import Environment, FileSystemLoader


def generate_readme() -> str:
    """Generate README content and return as string."""
    file_loader = FileSystemLoader('templates')
    env = Environment(loader=file_loader)
    template = env.get_template('readme_template')
    output = template.render(parsers=jc.lib.all_parser_info(),
                             info=jc.cli.JcCli.about_jc())
    return output


if __name__ == '__main__':
    content = generate_readme()

    if '--stdout' in sys.argv:
        sys.stdout.write(content)
        sys.stdout.flush()
    else:
        with open('README.md', 'w') as f:
            f.write(content)
