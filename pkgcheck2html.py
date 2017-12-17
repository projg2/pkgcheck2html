#!/usr/bin/env python
# vim:se fileencoding=utf8 :
# (c) 2015-2017 Michał Górny
# 2-clause BSD license

import argparse
import collections
import datetime
import io
import json
import os
import os.path
import sys
import xml.etree.ElementTree

import jinja2


class Result(object):
    def __init__(self, el, class_mapping):
        self._el = el
        self._class_mapping = class_mapping

    def __getattr__(self, key):
        return self._el.findtext(key) or ''

    @property
    def css_class(self):
        return self._class_mapping.get(getattr(self, 'class'), '')


def result_sort_key(r):
    return (r.category, r.package, r.version, getattr(r, 'class'), r.msg)


def get_results(input_paths, class_mapping):
    for input_path in input_paths:
        if input_path == '-':
            input_path = sys.stdin
        checks = xml.etree.ElementTree.parse(input_path).getroot()
        for r in checks:
            yield Result(r, class_mapping)


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


def find_of_class(it, cls, level = 2):
    out = collections.defaultdict(set)

    for g, r in group_results(it, level):
        for x in r:
            if x.css_class == cls:
                out[getattr(x, 'class')].add(g)

    return [(k, sorted(v)) for k, v in sorted(out.items())]


def get_result_timestamp(paths):
    for p in paths:
        st = os.stat(p)
        return datetime.datetime.utcfromtimestamp(st.st_mtime)


def main(*args):
    p = argparse.ArgumentParser()
    p.add_argument('-o', '--output', default='-',
            help='Output HTML file ("-" for stdout)')
    p.add_argument('-t', '--timestamp', default=None,
            help='Timestamp for results (git ISO8601-like UTC)')
    p.add_argument('files', nargs='+',
            help='Input XML files')
    args = p.parse_args(args)

    conf_path = os.path.join(os.path.dirname(__file__), 'pkgcheck2html.conf.json')
    with io.open(conf_path, 'r', encoding='utf8') as f:
        class_mapping = json.load(f)

    jenv = jinja2.Environment(
            loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
            extensions=['jinja2htmlcompress.HTMLCompress'])
    t = jenv.get_template('output.html.jinja')

    results = sorted(get_results(args.files, class_mapping), key=result_sort_key)

    types = {}
    for r in results:
        cl = getattr(r, 'class')
        if cl not in types:
            types[cl] = 0
        types[cl] += 1

    if args.timestamp is not None:
        ts = datetime.datetime.strptime(args.timestamp, '%Y-%m-%d %H:%M:%S')
    else:
        ts = get_result_timestamp(args.files)

    out = t.render(
        results = deep_group(results),
        warnings = find_of_class(results, 'warn'),
        staging = find_of_class(results, 'staging'),
        errors = find_of_class(results, 'err'),
        ts = ts,
    )

    if args.output == '-':
        sys.stdout.write(out)
    else:
        with io.open(args.output, 'w', encoding='utf8') as f:
            f.write(out)


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
