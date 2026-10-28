"""Stand-in for the ARK side: reads GAL1 records and prints the mapped Unreal camera.

Usage: python read_link.py [--path FILE] [--seconds N]
"""
import argparse
import time

import gal_link


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--path', default=str(gal_link.default_path()))
    parser.add_argument('--seconds', type=float, default=10)
    args = parser.parse_args()
    reader, origin, accepted = gal_link.Reader(args.path), None, 0
    end = time.monotonic() + args.seconds
    while time.monotonic() < end:
        r = reader.read()
        if r and not reader.stale():
            accepted += 1
            if origin is None:
                origin = (r.cam_pos, r.cam_rot[2])
            loc, rot = gal_link.to_unreal(r.cam_pos, r.cam_rot, origin[0], origin[1], (0, 0, 0), 0)
            if accepted % 30 == 1:
                print(f'seq {r.sequence:>7}  ue loc ({loc[0]:9.1f}, {loc[1]:9.1f}, {loc[2]:8.1f})  '
                      f'pitch {rot[0]:6.1f} yaw {rot[1]:7.1f} roll {rot[2]:5.1f}')
        elif reader.stale():
            print('stale' if reader.last_sequence is not None else 'waiting')
        time.sleep(1 / 30)
    print('accepted', accepted, 'records')


if __name__ == '__main__':
    main()
