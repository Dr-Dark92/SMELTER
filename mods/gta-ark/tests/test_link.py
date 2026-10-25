"""GAL1 record, seqlock and transform tests (no game needed)."""
import json
import struct
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import gal_link  # noqa: E402

FIELDS = ((1.0, 2.0, 3.0), (10.0, 0.0, 45.0), 50.0, (4.0, 5.0, 6.0), 90.0, 3, 7)


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'camera.bin'

    def test_layout_matches_the_spec(self):
        self.assertEqual(8 + gal_link.FIELDS.size, gal_link.SIZE)
        raw = gal_link.MAGIC + struct.pack('<I', 2) + gal_link.pack_fields(*FIELDS)
        self.assertEqual(struct.unpack_from('<f', raw, 32)[0], 50.0)   # fov at 32
        self.assertEqual(struct.unpack_from('<f', raw, 48)[0], 90.0)   # heading at 48
        self.assertEqual(struct.unpack_from('<I', raw, 52)[0], 3)      # flags at 52
        self.assertEqual(struct.unpack_from('<Q', raw, 56)[0], 7)      # frame at 56
        fixture = bytes.fromhex((ROOT / 'tests/gal1_fixture.hex').read_text())
        self.assertEqual(raw, fixture, 'The Lua fixture must be the exact Python/C++ GAL1 layout')

    def test_round_trip_and_rejections(self):
        writer = gal_link.Writer(self.path)
        self.addCleanup(writer.close)
        writer.write(*FIELDS)
        record = gal_link.Reader(self.path).read()
        self.assertEqual((record.cam_pos, record.fov, record.flags, record.frame), ((1.0, 2.0, 3.0), 50.0, 3, 7))
        self.assertEqual(record.sequence % 2, 0)
        raw = bytearray(self.path.read_bytes())
        odd = bytes(raw[:4]) + struct.pack('<I', record.sequence + 1) + bytes(raw[8:])
        self.assertIsNone(gal_link.unpack(odd))            # writer mid-update
        self.assertIsNone(gal_link.unpack(b'XXXX' + bytes(raw[4:])))  # foreign file
        self.assertIsNone(gal_link.unpack(bytes(raw[:63])))  # short file

    def test_writer_keeps_file_size_and_sequence_across_restarts(self):
        first = gal_link.Writer(self.path); first.write(*FIELDS); seq = first.sequence; first.close()
        second = gal_link.Writer(self.path)
        self.addCleanup(second.close)
        second.write(*FIELDS)
        self.assertEqual(second.sequence, seq + 2)
        self.assertEqual(self.path.stat().st_size, gal_link.SIZE)

    def test_reader_never_accepts_a_torn_record_under_concurrent_writes(self):
        writer = gal_link.Writer(self.path)
        self.addCleanup(writer.close)
        stop = threading.Event()

        def hammer():
            n = 0
            while not stop.is_set():
                n += 1
                v = float(n)
                writer.write((v, v, v), (v, v, v), v, (v, v, v), v, 2, n)
        thread = threading.Thread(target=hammer)
        thread.start()
        reader, accepted = gal_link.Reader(self.path), 0
        try:
            for _ in range(3000):
                r = reader.read()
                if r is None:
                    continue
                accepted += 1
                values = {*r.cam_pos, *r.cam_rot, r.fov, *r.player_pos, r.heading, float(r.frame)}
                self.assertEqual(len(values), 1, 'fields from two different writes were mixed')
        finally:
            stop.set(); thread.join()
        self.assertGreater(accepted, 0)

    def test_staleness(self):
        now = [0.0]
        writer = gal_link.Writer(self.path)
        self.addCleanup(writer.close)
        reader = gal_link.Reader(self.path, clock=lambda: now[0])
        self.assertTrue(reader.stale())  # nothing read yet
        writer.write(*FIELDS); reader.read()
        now[0] = 0.9; reader.read()
        self.assertFalse(reader.stale())
        now[0] = 1.2; reader.read()  # same sequence
        self.assertTrue(reader.stale())
        writer.write(*FIELDS); reader.read()
        self.assertFalse(reader.stale())


class TransformTests(unittest.TestCase):
    def test_shared_vectors(self):
        v = json.loads((ROOT / 'tests' / 'vectors.json').read_text(encoding='utf-8'))
        for case in v['cases']:
            with self.subTest(case['name']):
                loc, rot = gal_link.to_unreal(case['gta_pos'], case['gta_rot'], v['gta_origin'],
                                              v['gta_yaw_origin'], v['ue_origin'], v['ue_yaw_origin'])
                for got, want in zip(loc + rot, case['ue_loc'] + case['ue_rot']):
                    self.assertAlmostEqual(got, want, places=4)


class CrossLanguageTests(unittest.TestCase):
    def test_cpp_writer_output_if_built(self):
        """gta/build.bat runs gal_record_test.exe, which writes this sample with the C++ writer."""
        sample = ROOT / 'gta' / 'build' / 'cpp_sample.bin'
        if not sample.exists():
            self.skipTest('Build gta/ first (gta/build.bat) to produce the C++ sample')
        record = gal_link.unpack(sample.read_bytes())
        self.assertIsNotNone(record)
        self.assertEqual((record.cam_pos, record.cam_rot, record.fov), ((1.0, 2.0, 3.0), (10.0, 0.0, 45.0), 50.0))
        self.assertEqual((record.player_pos, record.heading, record.flags, record.frame), ((4.0, 5.0, 6.0), 90.0, 3, 7))


if __name__ == '__main__':
    unittest.main()
