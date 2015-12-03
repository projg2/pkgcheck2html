#!/usr/bin/env python
# vim:se fileencoding=utf8 :
# (c) 2015 Michał Górny

import sys
import xml.etree.ElementTree

import jinja2


class Result(object):
    def __init__(self, el):
        self._el = el

    def __getattr__(self, key):
        return self._el.findtext(key) or ''


def result_sort_key(r):
    return (r.category, r.package, r.version, getattr(r, 'class'), r.msg)


def get_results(input_paths):
    for input_path in input_paths:
        checks = xml.etree.ElementTree.parse(input_path).getroot()
        for r in checks:
            yield Result(r)


def split_result_group(it):
    for r in it:
        if not r.category:
            yield ((), r)
        elif not r.package:
            yield ((r.category,), r)
        elif not r.version:
            yield ((r.category, r.package), r)
        else:
            yield ((r.category, r.package, r.version), r)


def group_results(it, level = 3):
    prev_group = ()
    prev_l = []

    for g, r in split_result_group(it):
        if g[:level] != prev_group:
            if prev_l:
                yield (prev_group, prev_l)
            prev_group = g[:level]
            prev_l = []
        prev_l.append(r)
    yield (prev_group, prev_l)


def deep_group(it, level = 1):
    for g, r in group_results(it, level):
        if level > 3:
            for x in r:
                yield x
        else:
            yield (g, deep_group(r, level+1))


def main(*input_paths):
    jenv = jinja2.Environment(loader=jinja2.FileSystemLoader('.'))
    t = jenv.get_template('output.html')

    print(t.render(results = deep_group(
        sorted(get_results(input_paths), key=result_sort_key))))


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
