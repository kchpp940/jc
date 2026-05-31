#!/usr/bin/env python3
# Generate README-snap.md from jc metadata using jinja2 templates
import sys
import jc.lib
from jinja2 import Environment, FileSystemLoader


def generate_readme_snap() -> str:
    """Generate README-snap content and return as string."""
    file_loader = FileSystemLoader('templates')
    env = Environment(loader=file_loader)
    template = env.get_template('readme_snap_template')
    output = template.render(version=jc.lib.__version__)
    return output


if __name__ == '__main__':
    content = generate_readme_snap()

    if '--stdout' in sys.argv:
        sys.stdout.write(content)
        sys.stdout.flush()
    else:
        with open('README-snap.md', 'w') as f:
            f.write(content)
