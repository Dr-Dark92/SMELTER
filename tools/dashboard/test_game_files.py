"""inspect_game_files: header-only archive and executable inspection (synthetic files only)."""
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import game_files
from python_tools import ToolSession, permissions


def pe_bytes(code):
    """Minimal PE: MZ header, PE signature, one .text section holding `code`."""
    head = bytearray(0x200)
    head[:2] = b'MZ'
    struct.pack_into('<I', head, 0x3C, 0x40)
    head[0x40:0x44] = b'PE\0\0'
    struct.pack_into('<H', head, 0x46, 1)       # one section
    struct.pack_into('<H', head, 0x54, 0)       # no optional header
    section = 0x40 + 24
    head[section:section + 8] = b'.text\0\0\0'
    struct.pack_into('<II', head, section + 16, len(code), 0x200)
    return bytes(head) + code


class GameFilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        game = self.root / 'game'
        (game / 'Paks').mkdir(parents=True)
        (game / 'common.rpf').write_bytes(b'7FPR' + struct.pack('<3I', 705, 0, 0x0FEFFFFF))
        (game / 'open.rpf').write_bytes(b'7FPR' + struct.pack('<3I', 3, 0, 0x4E45504F))
        utoc = bytearray(96)
        utoc[:16] = b'-==--==--==--==-'
        utoc[16] = 8
        utoc[80] = 1 | 8  # compressed, indexed
        (game / 'Paks' / 'chunk0.utoc').write_bytes(bytes(utoc))
        pak = bytes(100) + bytes(16) + b'\0' + struct.pack('<II', 0x5A6F12E1, 12) + bytes(40)
        (game / 'Paks' / 'chunk0.pak').write_bytes(pak)
        (game / 'packed.exe').write_bytes(pe_bytes(bytes(range(256)) * 64))   # entropy 8.0
        (game / 'plain.exe').write_bytes(pe_bytes(b'\x90' * 4096))            # entropy 0.0
        (game / 'notes.txt').write_text('ignored')
        self.grants = {'inventory_root': str(game.resolve())}

    def run_tool(self, **arguments):
        with patch('access_policy.require'), patch('access_policy.allowed', return_value=True):
            return game_files.inspect(self.grants, {'relative_path': '.', **arguments})

    def test_reports_archive_formats_and_encryption(self):
        result = self.run_tool()
        self.assertEqual(result['archive_counts'], {'.rpf': 2, '.utoc': 1, '.pak': 1})
        kinds = ' | '.join(row['kind'] for row in result['archive_header_summary'])
        self.assertIn('encryption=NG', kinds)
        self.assertIn('encryption=none (OPEN)', kinds)
        utoc = next(s for s in result['archive_samples'] if s['path'].endswith('.utoc'))
        self.assertEqual((utoc['format'], utoc['encrypted'], utoc['compressed']), ('Unreal IoStore', False, True))
        pak = next(s for s in result['archive_samples'] if s['path'].endswith('.pak'))
        self.assertEqual((pak['version'], pak['encrypted_index']), (12, False))
        self.assertTrue(result['scan_complete'])

    def test_section_entropy_separates_packed_from_plain_code(self):
        exes = {e['path']: e for e in self.run_tool()['largest_executables']}
        self.assertEqual(exes['packed.exe']['sections'][0]['entropy_sample'], 8.0)
        self.assertEqual(exes['plain.exe']['sections'][0]['entropy_sample'], 0.0)

    def test_unknown_or_foreign_files_are_labelled_not_guessed(self):
        (self.root / 'game' / 'fake.rpf').write_bytes(b'not an archive')
        (self.root / 'game' / 'fake.exe').write_bytes(b'nope')
        result = self.run_tool()
        self.assertTrue(any('format=unknown' in row['kind'] for row in result['archive_header_summary']))
        self.assertEqual(next(e for e in result['largest_executables'] if e['path'] == 'fake.exe')['format'], 'not PE')

    def test_truncated_pak_footer_does_not_abort_other_files(self):
        (self.root / 'game' / 'truncated.pak').write_bytes(bytes(20) + struct.pack('<I', 0x5A6F12E1))
        result = self.run_tool()
        self.assertEqual(result['archive_counts']['.pak'], 2)
        self.assertTrue(result['largest_executables'])

    def test_flat_directory_entry_limit_reports_incomplete(self):
        with patch.object(game_files, 'MAX_VISITED', 2):
            result = self.run_tool()
        self.assertFalse(result['scan_complete'])
        self.assertIn('entry_scan_limit', result['scan_stop_reasons'])
        self.assertLessEqual(sum(result['archive_counts'].values()), 2)

    def test_requires_the_folder_grant_and_rejects_escapes(self):
        with self.assertRaisesRegex(ValueError, 'not approved'):
            game_files.inspect({'inventory_root': None}, {'relative_path': '.'})
        for bad in ('../x', 'C:/Windows', 'a\\b'):
            with self.assertRaises(ValueError):
                self.run_tool(relative_path=bad)

    def test_registered_only_with_the_inventory_grant(self):
        from tool_registry import schemas
        names = lambda g: {t['function']['name'] for t in schemas(g)}
        base = permissions(self.root, {})
        self.assertNotIn('inspect_game_files', names(base))
        self.assertIn('inspect_game_files', names({**base, 'inventory_root': self.grants['inventory_root']}))

    def test_receipt_line(self):
        session = ToolSession.__new__(ToolSession)
        session.tools, session.audit_path = [{}], 'audit.jsonl'
        session.events = [{'tool': 'inspect_game_files', 'reused': False, 'result': self.run_tool()}]
        self.assertIn('archives=', session.receipt())


if __name__ == '__main__':
    unittest.main()
