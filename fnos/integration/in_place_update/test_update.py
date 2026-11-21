import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fnos.integration.in_place_update import update


OLD = b'original compatibility script'
NEW = b'updated compatibility script'


class UpdateTest(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)
        self.old_digest = hashlib.sha256(OLD).hexdigest()
        self.patcher = patch.object(update, 'BASE_DIGEST', self.old_digest)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        for rel, data in ((update.RELEASE, update.BASE), (update.HELPER, OLD),
                          (Path('vol1/@homeassistant/config/configuration.yaml'), b'config'),
                          (Path('etc/passwd'), b'account')):
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.install = update.Installation(self.root, NEW)
        self.install.state.mkdir(mode=0o700, parents=True)

    def test_upgrade_rollback_and_reapply(self):
        self.assertEqual(self.install.status(), 'v0.3.2')
        self.install.apply()
        self.install.apply()
        self.assertEqual(self.install.status(), 'v0.3.3')
        self.assertEqual((self.root / update.HELPER).read_bytes(), NEW)
        self.install.rollback()
        self.install.rollback()
        self.assertEqual(self.install.status(), 'v0.3.2')
        self.assertEqual((self.root / update.HELPER).read_bytes(), OLD)
        self.assertEqual((self.root / 'etc/passwd').read_bytes(), b'account')
        self.assertEqual((self.root / 'vol1/@homeassistant/config/configuration.yaml').read_bytes(), b'config')
        self.install.apply()
        self.assertEqual(self.install.status(), 'v0.3.3')

    def test_interrupted_upgrade_can_be_rolled_back_or_resumed(self):
        for resume in (self.install.rollback, self.install.apply):
            with patch.object(self.install, 'set_release', side_effect=OSError('interrupted')):
                with self.assertRaises(OSError):
                    self.install.apply()
            self.assertEqual(self.install.status(), 'interrupted')
            resume()
            self.assertNotEqual(self.install.status(), 'interrupted')
        self.assertEqual(self.install.status(), 'v0.3.3')

    def test_foreign_version_or_helper_is_rejected(self):
        release = self.root / update.RELEASE
        release.write_bytes(b'v0.3.1\n')
        with self.assertRaises(ValueError):
            self.install.apply()
        release.write_bytes(update.BASE)
        (self.root / update.HELPER).write_bytes(b'local modification')
        with self.assertRaises(ValueError):
            self.install.apply()
        self.assertEqual(release.read_bytes(), update.BASE)
        self.assertFalse(self.install.backup.exists())
