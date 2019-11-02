#!/usr/bin/env python
# vim:se fileencoding=utf8 :
# (c) 2015-2019 Michał Górny
# 2-clause BSD license

import argparse
import io
import json
import os
import os.path
import sys
import lxml.etree


def get_results(input_paths):
    for input_path in input_paths:
        if input_path == '-':
            input_path = sys.stdin
        checks = lxml.etree.parse(input_path).getroot()
        for r in checks:
            yield r


def main(*args):
    p = argparse.ArgumentParser()
    p.add_argument('-c', '--class', dest='cls', action='append',
            required=True,
            help='Class to ignore existing violations for')
    p.add_argument('-o', '--output', required=True,
            help='Output JSON file (data will be merged if it exists)')
    p.add_argument('files', nargs='+',
            help='Input XML files')
    args = p.parse_args(args)

    try:
        with open(args.output) as f:
            out = json.load(f)
    except OSError:
        out = {}

    for r in get_results(args.files):
        cls = r.findtext('class')
        if cls in args.cls:
            cat, pkg, ver = (r.findtext(x, '')
                             for x in ('category', 'package', 'version'))
            if cat not in out:
                out[cat] = {}
            if pkg not in out[cat]:
                out[cat][pkg] = {}
            if ver not in out[cat][pkg]:
                out[cat][pkg][ver] = []
            if cls not in out[cat][pkg][ver]:
                out[cat][pkg][ver].append(cls)

    with open(args.output, 'w') as f:
        json.dump(out, f)


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
