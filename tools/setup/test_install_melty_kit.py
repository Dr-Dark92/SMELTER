"""Disposable safe-extraction/install checks; no remote downloads or kit execution."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch

import install_melty_kit as kit


class InstallMeltyKitTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.root = self.base / 'checkout'
        self.root.mkdir()
        self.archive = self.base / 'kit.tar.gz'

    def fixture(self, extra=None, metadata_change=None):
        content = {'skills/mod-any-game/SKILL.md': b'fixture skill', 'bin/um': b'fixture launcher never executed'}
        pin = {**kit.PIN, 'files': len(content), 'bytes': sum(map(len, content.values()))}
        manifest = {key: value for key, value in pin.items() if key != 'archive_sha256'}
        manifest['fileHashes'] = {name: hashlib.sha256(raw).hexdigest() for name, raw in content.items()}
        if metadata_change:
            metadata_change(manifest)
        files = {**content, 'MELTY-KIT.json': json.dumps(manifest).encode(), 'MELTY.md': b'fixture metadata'}
        with tarfile.open(self.archive, 'w:gz') as archive:
            for name, raw in files.items():
                member = tarfile.TarInfo(name)
                member.size = len(raw)
                archive.addfile(member, io.BytesIO(raw))
            if extra:
                extra(archive)
        pin['archive_sha256'] = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        return pin

    def test_verified_install_is_local_and_idempotent(self):
        pin = self.fixture()
        downloader = Mock(side_effect=AssertionError('local archive must avoid network'))
        with patch.object(kit, 'PIN', pin):
            result = kit.install(self.root, archive=self.archive, downloader=downloader)
            self.assertEqual(result['status'], 'installed')
            self.assertEqual(Path(result['directory']), self.root / '.smelter/tooling/melty')
            self.assertFalse(result['connected'])
            self.assertFalse(result['executed'])
            self.assertEqual(result['archive_sha256'], pin['archive_sha256'])
            self.assertEqual(kit.install(self.root, archive=self.archive)['status'], 'already_installed')
        downloader.assert_not_called()

    def test_divergent_existing_install_is_preserved(self):
        pin = self.fixture()
        with patch.object(kit, 'PIN', pin):
            kit.install(self.root, archive=self.archive)
            target = kit.destination(self.root) / 'bin/um'
            target.write_bytes(b'local change')
            with self.assertRaisesRegex(ValueError, 'divergent'):
                kit.install(self.root, archive=self.archive)
            self.assertEqual(target.read_bytes(), b'local change')

    def test_unmanaged_destination_is_preserved(self):
        destination = kit.destination(self.root)
        destination.mkdir(parents=True)
        (destination / 'keep.txt').write_text('keep')
        with self.assertRaisesRegex(ValueError, 'refusing overwrite'):
            kit.install(self.root)
        self.assertEqual((destination / 'keep.txt').read_text(), 'keep')

    def test_archive_digest_mismatch_installs_nothing(self):
        self.fixture()
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            kit.install(self.root, archive=self.archive)
        self.assertFalse(kit.destination(self.root).exists())
        self.assertEqual(list(kit.destination(self.root).parent.glob('melty-stage-*')), [])

    def test_member_checksum_failure_rolls_back_staging(self):
        pin = self.fixture(metadata_change=lambda d: d['fileHashes'].__setitem__('bin/um', '0' * 64))
        with patch.object(kit, 'PIN', pin), self.assertRaisesRegex(ValueError, 'checksum'):
            kit.install(self.root, archive=self.archive)
        self.assertFalse(kit.destination(self.root).exists())

    def test_links_traversal_absolute_and_special_members_rejected(self):
        def add_member(name, kind):
            def add(archive):
                member = tarfile.TarInfo(name)
                member.type = kind
                member.linkname = '../../outside'
                archive.addfile(member)
            return add
        for name, kind in (('../escape', tarfile.REGTYPE), ('/absolute', tarfile.REGTYPE),
                           ('link', tarfile.SYMTYPE), ('hard', tarfile.LNKTYPE),
                           ('fifo', tarfile.FIFOTYPE), ('dir\\escape', tarfile.REGTYPE),
                           ('CON.txt', tarfile.REGTYPE)):
            with self.subTest(name=name):
                pin = self.fixture(extra=add_member(name, kind))
                with patch.object(kit, 'PIN', pin), self.assertRaises(ValueError):
                    kit.install(self.root, archive=self.archive)
                self.assertFalse(kit.destination(self.root).exists())

    def test_undeclared_and_colliding_members_are_rejected(self):
        for name in ('extra.py', 'BIN/UM'):
            def add(archive):
                member = tarfile.TarInfo(name)
                archive.addfile(member, io.BytesIO())
            pin = self.fixture(extra=add)
            with self.subTest(name=name), patch.object(kit, 'PIN', pin), self.assertRaises(ValueError):
                kit.install(self.root, archive=self.archive)

    def test_expanded_and_archive_limits_are_enforced(self):
        pin = self.fixture()
        with patch.object(kit, 'PIN', pin), patch.object(kit, 'MAX_EXPANDED', 2), self.assertRaisesRegex(ValueError, 'expanded'):
            kit.install(self.root, archive=self.archive)
        with patch.object(kit, 'PIN', pin), patch.object(kit, 'MAX_ARCHIVE', 2), self.assertRaisesRegex(ValueError, 'oversized'):
            kit.install(self.root, archive=self.archive)

    def test_missing_install_check_does_not_download(self):
        self.assertEqual(kit.check(self.root)['status'], 'missing')
        self.assertFalse(kit.destination(self.root).exists())

    def test_download_is_fixed_url_bounded_and_credential_free(self):
        output = self.base / 'download.tar.gz'
        response = io.BytesIO(b'fixture')
        opener = Mock(return_value=response)
        self.assertEqual(kit._download(output, opener=opener), 7)
        request = opener.call_args.args[0]
        self.assertEqual(request.full_url, kit.URL)
        self.assertNotIn('Authorization', request.headers)
        output.unlink()
        with patch.object(kit, 'MAX_ARCHIVE', 2), self.assertRaisesRegex(ValueError, 'compressed'):
            kit._download(output, opener=lambda *a, **k: io.BytesIO(b'long'))

    def test_download_redirect_and_relative_checkout_are_rejected(self):
        response = io.BytesIO(b'fixture')
        response.geturl = lambda: 'https://example.invalid/redirect'
        with self.assertRaisesRegex(ValueError, 'redirect'):
            kit._download(self.base/'download', opener=lambda *a, **k: response)
        with self.assertRaises(ValueError):
            kit.destination('relative')

    def test_only_one_observed_official_redirect_is_allowed(self):
        from urllib.request import Request
        destination='https://'+kit.CDN_HOST+kit.CDN_PATH+'?signed=fixture'
        handler=kit._OfficialRedirect()
        request=handler.redirect_request(Request(kit.URL,headers={'Authorization':'private'}),None,302,'',{},destination)
        self.assertEqual(request.full_url,destination)
        self.assertNotIn('Authorization',request.headers)
        self.assertIsNone(handler.redirect_request(Request(destination),None,302,'',{},destination))
        for bad in ('http://'+kit.CDN_HOST+kit.CDN_PATH,'https://attacker.invalid'+kit.CDN_PATH,
                    'https://'+kit.CDN_HOST+'/other.tar.gz'):
            with self.subTest(bad=bad):
                self.assertIsNone(handler.redirect_request(Request(kit.URL),None,302,'',{},bad))


if __name__ == '__main__':
    unittest.main()
