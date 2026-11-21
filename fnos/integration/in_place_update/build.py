"""Build the standalone Linux update package using Python's standard library."""

import argparse
from pathlib import Path
import stat
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


def build(output):
    source = Path(__file__).resolve().parent
    entries = {
        '__main__.py': b'from update import main\nmain()\n',
        'update.py': (source / 'update.py').read_bytes(),
        'quark_log_compat.py': (source.parent / 'image_assembly/quark_log_compat.py').read_bytes(),
    }
    with output.open('xb') as stream, ZipFile(stream, 'w') as package:
        for name, contents in entries.items():
            member = ZipInfo(name, (2026, 11, 21, 0, 0, 0))
            member.create_system = 3
            member.external_attr = (stat.S_IFREG | 0o644) << 16
            package.writestr(member, contents.replace(b'\r\n', b'\n'), compress_type=ZIP_DEFLATED)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    build(parser.parse_args().output)
