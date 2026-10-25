"""Melty readiness contracts; fixtures only, never a live account or kit process."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError

import melty_connection as melty


def manifest():
    return {'name': "Melty's modding kit", 'version': melty.KIT_VERSION,
            'hash': melty.KIT_HASH, 'files': 555, 'bytes': 23282319}


class MeltyConnectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve() / 'kit'

    def install_fixture(self):
        data = manifest()
        data['fileHashes'] = {}
        for relative in melty.REQUIRED_FILES:
            item = self.base / relative
            item.parent.mkdir(parents=True, exist_ok=True)
            raw = ('fixture:' + relative).encode()
            item.write_bytes(raw)
            data['fileHashes'][relative] = hashlib.sha256(raw).hexdigest()
        (self.base / 'MELTY-KIT.json').write_text(json.dumps(data), encoding='utf-8')
        return data

    def test_missing_kit_is_not_connected_and_does_not_start_anything(self):
        result = melty.status(kit_directory=self.base)
        self.assertEqual(result['kit']['state'], 'missing')
        self.assertFalse(result['connected'])
        self.assertEqual(result['actions_enabled'], [])
        self.assertFalse(result['executed'])

    def test_present_kit_does_not_imply_mcp_connection(self):
        self.install_fixture()
        result = melty.status(kit_directory=self.base)
        self.assertEqual(result['kit']['state'], 'present')
        self.assertTrue(result['kit']['critical_files_match_manifest'])
        self.assertFalse(result['connected'])
        self.assertTrue(result['endpoint_verified'])  # Independently verified fixed service URL.
        self.assertFalse(result['authentication_verified'])

    def test_modified_critical_file_is_detected(self):
        self.install_fixture()
        (self.base / melty.REQUIRED_FILES[0]).write_text('changed')
        result = melty.kit_status(directory=self.base)
        self.assertEqual(result['state'], 'invalid')
        self.assertIn('differs', result['reason'])

    def test_version_drift_is_distinct_from_absent_installation(self):
        data = self.install_fixture()
        data['version'] = 'future'
        (self.base / 'MELTY-KIT.json').write_text(json.dumps(data))
        self.assertEqual(melty.kit_status(directory=self.base)['state'], 'version_mismatch')

    def test_oversized_manifest_and_missing_hashes_are_invalid(self):
        self.install_fixture()
        with patch.object(melty, 'MAX_MANIFEST', 4):
            self.assertEqual(melty.kit_status(directory=self.base)['state'], 'invalid')
        data = manifest()
        (self.base / 'MELTY-KIT.json').write_text(json.dumps(data))
        self.assertEqual(melty.kit_status(directory=self.base)['state'], 'invalid')

    def test_symlinked_kit_is_rejected(self):
        self.install_fixture()
        link = self.base.with_name('linked')
        try:
            link.symlink_to(self.base, target_is_directory=True)
        except OSError:
            self.skipTest('Symlink privilege unavailable')
        self.assertEqual(melty.kit_status(directory=link)['state'], 'invalid')

    def test_relative_and_traversal_kit_locations_are_invalid(self):
        for location in ('relative', str(self.base / '..')):
            self.assertEqual(melty.kit_status(directory=location)['state'], 'invalid')

    def test_public_manifest_probe_sends_no_account_credentials(self):
        opener = Mock(return_value=io.BytesIO(json.dumps(manifest()).encode()))
        result = melty.public_kit_manifest(opener=opener)
        request = opener.call_args.args[0]
        self.assertEqual(request.full_url, melty.KIT_MANIFEST_URL)
        self.assertNotIn('Authorization', request.headers)
        self.assertEqual(opener.call_args.kwargs, {'timeout': 10})
        self.assertTrue(result['matches_pin'])
        self.assertFalse(result['connected'])

    def test_public_manifest_rejects_drift_without_claiming_connection(self):
        data = manifest()
        data['version'] = 'new'
        result = melty.public_kit_manifest(opener=lambda *a, **k: io.BytesIO(json.dumps(data).encode()))
        self.assertFalse(result['matches_pin'])
        self.assertFalse(result['connected'])

    def test_public_manifest_rejects_redirects(self):
        response = io.BytesIO(json.dumps(manifest()).encode())
        response.geturl = lambda: 'https://example.invalid/redirect'
        with self.assertRaisesRegex(ValueError, 'redirect'):
            melty.public_kit_manifest(opener=lambda *a, **k: response)

    def test_public_manifest_rejects_size_json_and_invalid_fields(self):
        for raw in (b'x' * (melty.MAX_MANIFEST + 1), b'not json', b'{}',
                    json.dumps({**manifest(), 'files': True}).encode()):
            with self.subTest(raw=raw[:20]), self.assertRaises(ValueError):
                melty.public_kit_manifest(opener=lambda *a, **k: io.BytesIO(raw))

    def test_transport_errors_do_not_reflect_private_exception_text(self):
        with self.assertRaises(ValueError) as error:
            melty.public_kit_manifest(opener=Mock(side_effect=URLError('secret fixture')))
        self.assertNotIn('secret fixture', str(error.exception))

    def test_remote_calls_are_explicitly_blocked(self):
        with self.assertRaisesRegex(ValueError, 'endpoint, transport and authentication'):
            melty.require_connection()


if __name__ == '__main__':
    unittest.main()
