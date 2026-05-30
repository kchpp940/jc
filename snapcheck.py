#!/usr/bin/env python3
# Validate that snapcraft.yaml matches jc release metadata
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("snapcheck: PyYAML required (pip install pyyaml)", file=sys.stderr)
    sys.exit(1)

from docgen import release


def main():
    snapcraft_path = Path(__file__).parent / 'snap' / 'snapcraft.yaml'
    with open(snapcraft_path) as f:
        snap = yaml.safe_load(f)

    rel = release()
    snap_meta = rel['snap']

    checks = [
        ('base', snap.get('base'), snap_meta['base']),
        ('confinement', snap.get('confinement'), snap_meta['confinement']),
        ('license', snap.get('license'), rel['license']),
        ('website', snap.get('website'), rel['website']),
        ('source-code', snap.get('source-code'), rel['website']),
    ]

    expected_contact = f"{rel['author']} <{rel['author_email']}>"
    checks.append(('contact', snap.get('contact'), expected_contact))

    errors = 0
    for field, actual, expected in checks:
        if actual != expected:
            print(f"snapcheck: FAIL {field}")
            print(f"  expected (from __release__): {expected}")
            print(f"  actual (in snapcraft.yaml): {actual}")
            errors += 1

    if errors == 0:
        print(f"snapcheck: {len(checks)} fields OK")
        return 0
    else:
        print(f"\nsnapcheck: {errors} field(s) out of sync with __release__")
        print("  Update snap/snapcraft.yaml after changing jc/lib.py __release__")
        return 1


if __name__ == '__main__':
    sys.exit(main())
