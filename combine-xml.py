#!/usr/bin/env python
# vim:se fileencoding=utf8 :
# (c) 2016 Michał Górny

import sys
import lxml.etree


def get_trees(paths):
    for input_path in paths:
        yield lxml.etree.parse(input_path)


def main(*args):
    i = iter(get_trees(args))
    res_tree = next(i)
    for tree in i:
        for x in tree.getroot():
            res_tree.getroot().append(x)
    res_tree.write(sys.stdout.buffer, encoding='utf8', xml_declaration=True)
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
