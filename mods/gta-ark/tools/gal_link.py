"""Reference implementation of the GAL1 link record (see ../link-format.md).

Used by the offline tools and tests; the C++ writer and the Lua reader must agree with it.
"""
import os
import math
import struct
import time
from dataclasses import dataclass
from pathlib import Path

MAGIC = b'GAL1'
SIZE = 64
FIELDS = struct.Struct('<3f3ff3ffIQ')  # offsets 8..63
FLAG_STORY = 1
FLAG_ENABLED = 2
STALE_SECONDS = 1.0


def default_path():
    return Path(os.environ.get('LOCALAPPDATA', '.')) / 'SMELTER' / 'gta-ark-link' / 'camera.bin'


@dataclass
class Record:
    sequence: int
    cam_pos: tuple
    cam_rot: tuple  # pitch, roll, yaw (GTA order 2), degrees
    fov: float
    player_pos: tuple
    heading: float
    flags: int
    frame: int


def pack_fields(cam_pos, cam_rot, fov, player_pos, heading, flags, frame):
    return FIELDS.pack(*cam_pos, *cam_rot, fov, *player_pos, heading, flags, frame)


def unpack(raw):
    """Return a Record for a complete record, or None for torn, foreign or in-progress data."""
    if len(raw) != SIZE or raw[:4] != MAGIC:
        return None
    sequence = struct.unpack_from('<I', raw, 4)[0]
    if sequence % 2:
        return None
    v = FIELDS.unpack_from(raw, 8)
    if not all(math.isfinite(n) for n in v[:11]) or not 0 < v[6] < 180:
        return None
    return Record(sequence, v[0:3], v[3:6], v[6], v[7:10], v[10], v[11], v[12])


class Writer:
    """Seqlock writer: odd sequence while writing, even when complete, file never truncated."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists() or self.path.stat().st_size != SIZE:
            self.path.write_bytes(MAGIC + bytes(SIZE - 4))
        self.file = open(self.path, 'r+b', buffering=0)
        self.sequence = struct.unpack('<I', self.path.read_bytes()[4:8])[0] & ~1

    def write(self, *fields):
        f = self.file
        f.seek(4); f.write(struct.pack('<I', self.sequence + 1))
        f.seek(8); f.write(pack_fields(*fields))
        self.sequence += 2
        f.seek(4); f.write(struct.pack('<I', self.sequence))

    def close(self):
        self.file.close()


class Reader:
    """Accepts a record only when two consecutive reads agree; tracks staleness."""

    def __init__(self, path, stale_seconds=STALE_SECONDS, clock=time.monotonic):
        self.path, self.stale_seconds, self.clock = Path(path), stale_seconds, clock
        self.last_sequence, self.last_change = None, None

    def read(self):
        try:
            with open(self.path, 'rb') as f:
                first = f.read(SIZE); f.seek(0); second = f.read(SIZE)
        except OSError:
            return None
        if first != second:
            return None
        record = unpack(first)
        if record is not None and record.sequence != self.last_sequence:
            self.last_sequence, self.last_change = record.sequence, self.clock()
        return record

    def stale(self):
        return self.last_change is None or self.clock() - self.last_change > self.stale_seconds


def to_unreal(gta_pos, gta_rot, gta_origin, gta_yaw_origin, ue_origin, ue_yaw_origin):
    """Map a GTA camera to an Unreal location (cm) and rotator (pitch, yaw, roll), relative to link start."""
    dx, dy, dz = (gta_pos[i] - gta_origin[i] for i in range(3))
    location = (ue_origin[0] + 100 * dy, ue_origin[1] + 100 * dx, ue_origin[2] + 100 * dz)
    pitch, roll, yaw = gta_rot
    ue_yaw = (ue_yaw_origin - (yaw - gta_yaw_origin) + 180) % 360 - 180
    return location, (pitch, ue_yaw, -roll)
