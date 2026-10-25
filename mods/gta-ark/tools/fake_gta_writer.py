"""Stand-in for GTA: writes GAL1 records of a camera walking north and turning, for testing the ARK side.

Usage: python fake_gta_writer.py [--path FILE] [--seconds N] [--hz 60]
"""
import argparse
import math
import time

import gal_link


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--path', default=str(gal_link.default_path()))
    parser.add_argument('--seconds', type=float, default=30)
    parser.add_argument('--hz', type=float, default=60)
    args = parser.parse_args()
    writer = gal_link.Writer(args.path)
    start, frame = time.monotonic(), 0
    print('writing', args.path)
    try:
        while (t := time.monotonic() - start) < args.seconds:
            frame += 1
            yaw = 45 * math.sin(t / 3)  # sweep left and right
            pos = (0.0, 1.4 * t, 30.0)  # walk north at 1.4 m/s
            writer.write(pos, (0.0, 0.0, yaw), 50.0, (pos[0], pos[1], pos[2] - 1.6), yaw,
                         gal_link.FLAG_STORY | gal_link.FLAG_ENABLED, frame)
            time.sleep(1 / args.hz)
    finally:
        writer.close()
    print('stopped after', frame, 'records')


if __name__ == '__main__':
    main()
