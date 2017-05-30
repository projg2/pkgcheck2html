#!/usr/bin/env python
# vim:se fileencoding=utf8 :
# (c) 2015-2016 Michał Górny
# 2-clause BSD license

import json
import subprocess
import sys


def main(json_path):
    s = subprocess.Popen(['pkgcheck', '--list-keywords'],
            stdout=subprocess.PIPE)
    sout, serr = s.communicate()
    all_classes = sout.decode().split()

    with open(json_path, 'r') as f:
        conf = json.load(f)

    new_conf = dict((k, conf.get(str(k), '')) for k in all_classes)
    with open(json_path, 'w') as f:
        json.dump(new_conf, f, sort_keys=True, indent=4)


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
