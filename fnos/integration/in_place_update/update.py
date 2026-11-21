"""Install and roll back the v0.3.3 update on the supported X5 image."""

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import zipfile


BASE = b'v0.3.2\n'
TARGET = b'v0.3.3\n'
BASE_DIGEST = '6c91f145426dfc55ad9b03b448949f02d36394a30255cea021084b672d1dd5c6'
RELEASE = Path('etc/fnos-x5/release')
HELPER = Path('usr/lib/fnos-x5/quark_log_compat.py')
STATE = Path('var/lib/fnos-x5/update-v0.3.3')


def trusted_path(path, mode):
    info = path.lstat()
    if info.st_uid or info.st_gid or info.st_mode != mode:
        raise ValueError(f'Unexpected ownership or mode: {path}')


def trust_parents(path, root):
    for parent in path.parents:
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid or info.st_mode & 0o022:
            raise ValueError(f'Unsafe parent directory: {parent}')
        if parent == root:
            return


def read_file(path, mode=0o644):
    trusted_path(path, stat.S_IFREG | mode)
    return path.read_bytes()


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_write(path, contents, mode):
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            os.fchmod(output.fileno(), mode)
            output.write(contents)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        sync_dir(path.parent)
    finally:
        Path(temporary).unlink(missing_ok=True)


class Installation:
    def __init__(self, root, payload):
        self.root = root
        self.payload = payload
        self.release = root / RELEASE
        self.helper = root / HELPER
        self.state = root / STATE
        self.backup = self.state / 'original-helper.py'

    @contextmanager
    def locked(self):
        trust_parents(self.state, self.root)
        self.state.mkdir(mode=0o700, exist_ok=True)
        trusted_path(self.state, stat.S_IFDIR | 0o700)
        sync_dir(self.state.parent)
        fd = os.open(self.state / 'lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally:
            os.close(fd)

    def inspect(self):
        trust_parents(self.release, self.root)
        trust_parents(self.helper, self.root)
        version = read_file(self.release)
        if version not in (BASE, TARGET):
            raise ValueError('This update requires the v0.3.2 or v0.3.3 RDK X5 image')
        contents = read_file(self.helper)
        original = hashlib.sha256(contents).hexdigest() == BASE_DIGEST
        if not original and contents != self.payload:
            raise ValueError(f'Unrecognized local file: {self.helper}')
        return version, original, contents

    def original_backup(self):
        original = read_file(self.backup, 0o600)
        if hashlib.sha256(original).hexdigest() != BASE_DIGEST:
            raise ValueError('Rollback backup failed checksum validation')
        return original

    def status(self):
        version, original, _ = self.inspect()
        if not original or version == TARGET:
            self.original_backup()
        if original != (version == BASE):
            return 'interrupted'
        return version.decode().strip()

    def set_release(self, version):
        atomic_write(self.release, version, 0o644)

    def apply(self):
        version, original, contents = self.inspect()
        try:
            self.original_backup()
        except FileNotFoundError:
            if not original or version != BASE:
                raise ValueError('The original rollback backup is missing') from None
            atomic_write(self.backup, contents, 0o600)
        if original:
            atomic_write(self.helper, self.payload, 0o644)
        if version != TARGET:
            self.set_release(TARGET)

    def rollback(self):
        version, original, _ = self.inspect()
        if original and version == BASE:
            return
        backup = self.original_backup()
        if not original:
            atomic_write(self.helper, backup, 0o644)
        if version != BASE:
            self.set_release(BASE)


def check_board():
    model = Path('/proc/device-tree/model').read_bytes().rstrip(b'\0')
    root_volume = subprocess.check_output(['findmnt', '-nro', 'SOURCE,FSTYPE', '/'], text=True).strip()
    trim = subprocess.check_output(['dpkg-query', '-W', '-f=${Version}', 'trim'], text=True)
    if (not model.startswith(b'D-Robotics RDK X5') or os.uname().release != '6.18.0'
            or not re.fullmatch(r'/dev/mmcblk[0-9]+p2 ext4', root_volume) or trim != '1.2.0701'):
        raise ValueError('Unsupported board, system partition, kernel or fnOS version')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('status', 'apply', 'rollback'))
    args = parser.parse_args()
    if os.geteuid():
        parser.exit(1, 'Run the package with sudo.\n')
    try:
        check_board()
        with zipfile.ZipFile(sys.argv[0]) as archive:
            payload = archive.read('quark_log_compat.py')
        install = Installation(Path('/'), payload)
        with install.locked():
            if args.action == 'apply':
                install.apply()
            elif args.action == 'rollback':
                install.rollback()
            print(install.status())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        parser.exit(1, f'Update stopped: {error}\n')
