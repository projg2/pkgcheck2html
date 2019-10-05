#!/usr/bin/env python
# vim:se fileencoding=utf8 :
# (c) 2015-2019 Michał Górny
# 2-clause BSD license

import argparse
import json
import subprocess
import sys


def main(argv):
    argp = argparse.ArgumentParser(prog=argv[0])
    argp.add_argument('--delete-old', action='store_true',
                      help='Delete old options (kept by default)')
    argp.add_argument('path',
                      help='Path to .conf file')
    args = argp.parse_args(argv[1:])

    s = subprocess.Popen(['pkgcheck', 'show', '--keywords'],
            stdout=subprocess.PIPE)
    sout, serr = s.communicate()
    all_classes = sout.decode().split()

    with open(args.path, 'r') as f:
        conf = json.load(f)

    if not args.delete_old:
        all_classes.extend(conf.keys())
    new_conf = dict((k, conf.get(str(k), '')) for k in all_classes)

    with open(args.path, 'w') as f:
        json.dump(new_conf, f, sort_keys=True, indent=4)

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
