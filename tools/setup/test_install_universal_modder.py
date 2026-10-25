import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from install_universal_modder import extract, install

REVISION = 'a' * 40


class UniversalModderInstallerTests(unittest.TestCase):
    def test_archive_traversal_links_and_duplicates_fail_before_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for index, names in enumerate((['../escape'], ['um/x.py', 'um/X.py'], ['um/link'])):
                archive = base / (str(index) + '.zip')
                with zipfile.ZipFile(archive, 'w') as bundle:
                    for name in names:
                        member = zipfile.ZipInfo('universal-modder-' + REVISION + '/' + name)
                        if name.endswith('link'):
                            member.create_system = 3
                            member.external_attr = (stat.S_IFLNK | 0o777) << 16
                        bundle.writestr(member, 'fixture')
                destination = base / ('out' + str(index))
                with self.assertRaises(ValueError):extract(archive, destination, REVISION)
                self.assertFalse(destination.exists())

    def test_valid_source_does_not_overwrite_an_existing_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); archive = base / 'source.zip'
            with zipfile.ZipFile(archive, 'w') as bundle:
                bundle.writestr('universal-modder-' + REVISION + '/um/__init__.py', 'fixture')
            destination = base / 'source'
            extract(archive, destination, REVISION)
            with self.assertRaises(ValueError):extract(archive, destination, REVISION)
            self.assertEqual((destination / 'um/__init__.py').read_text(), 'fixture')

    def test_wrong_checksum_fails_before_dependency_installation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); archive = root / 'source.zip'; archive.write_bytes(b'not the reviewed archive')
            pin = {'revision':REVISION, 'sha256':'0' * 64}
            (root / 'system-requirements.json').write_text(json.dumps({'setup':{'universal_modder':pin}}))
            with patch('install_universal_modder.subprocess.run') as process:
                with self.assertRaisesRegex(ValueError, 'checksum'):install(root, archive)
                process.assert_not_called()
