#!/usr/bin/env python
# vim:se fileencoding=utf8 :
# (c) 2015-2016 Michał Górny
# 2-clause BSD license

import argparse
import datetime
import io
import os
import os.path
import sys
import xml.etree.ElementTree

import jinja2


class_mapping = {
    "NonsolvableDeps": 'err',
    "MissingManifest": 'err',
    "UnknownManifest": 'err',
    "ConflictingChksums": 'err',
    "MetadataError": 'err',
    "CrappyDescription": 'warn',
    "UnusedLocalFlags": 'err',
#    "UnusedGlobalFlags": 'warn',
    "PkgBadlyFormedXml": 'err',
    "CatBadlyFormedXml": 'err',
    "PkgInvalidXml": 'err',
    "CatInvalidXml": 'err',
    "UnstatedIUSE": 'err',
    "VisibleVcsPkg": 'err',
#    "ExecutableFile": 'warn',
    "MetadataLoadError": 'err',
    "NoFinalNewline": 'err',
    "WrongIndentFound": 'err',
#    "WhitespaceFound": 'warn',
    "MissingUri": 'warn',
    "MissingChksum": 'warn',
    "Glep31Violation": 'err',

    # repo-mirror-ci pkgcheck fork specific
    "PkgMetadataXmlInvalidPkgRef": 'err',
    "CatMetadataXmlInvalidPkgRef": 'err',
    "PkgMetadataXmlInvalidCatRef": 'err',
    "CatMetadataXmlInvalidCatRef": 'err',
    "PkgMetadataXmlInvalidProjectError": 'err',
}


class Result(object):
    def __init__(self, el):
        self._el = el

    def __getattr__(self, key):
        return self._el.findtext(key) or ''

    @property
    def css_class(self):
        return class_mapping.get(getattr(self, 'class'), '')


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


def find_of_class(it, cls, level = 2):
    for g, r in group_results(it, level):
        for x in r:
            if x.css_class == cls:
                yield g
                break


def get_result_timestamp(paths):
    for p in paths:
        st = os.stat(p)
        return datetime.datetime.utcfromtimestamp(st.st_mtime)


def main(*args):
    p = argparse.ArgumentParser()
    p.add_argument('-o', '--output', default='output.html',
            help='Output HTML file ("-" for stdout)')
    p.add_argument('-b', '--borked', default='borked.list',
            help='Output borked.list file')
    p.add_argument('-t', '--timestamp', default=None,
            help='Timestamp for results (git ISO8601-like UTC)')
    p.add_argument('files', nargs='+',
            help='Input XML files')
    args = p.parse_args(args)

    jenv = jinja2.Environment(
            loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
            extensions=['jinja2htmlcompress.HTMLCompress'])
    t = jenv.get_template('output.html.jinja')

    results = sorted(get_results(args.files), key=result_sort_key)

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
        warnings = list(find_of_class(results, 'warn')),
        errors = list(find_of_class(results, 'err')),
        ts = ts,
    )

    if args.output == '-':
        sys.stdout.write(out)
    else:
        with io.open(args.output, 'w', encoding='utf8') as f:
            f.write(out)

    with open(args.borked, 'w') as f:
        for g in find_of_class(results, 'err'):
            f.write('output.html#%s\n' % '/'.join(g[:2]))


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
