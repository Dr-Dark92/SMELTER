"""Render the static graph into a self-contained, offline relationship explorer."""
import argparse
import base64
import gzip
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('graph',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();data=base64.b64encode(gzip.compress(args.graph.read_bytes(),mtime=0)).decode()
    template=Path(__file__).with_name('system_graph_template.html').read_text()
    args.output.write_text(template.replace('__GRAPH_BASE64__',data),encoding='utf-8')
    print(str(args.output))


if __name__=='__main__':main()
