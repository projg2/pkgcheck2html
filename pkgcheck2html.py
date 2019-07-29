#!/usr/bin/env python
# vim:se fileencoding=utf8 :
# (c) 2015-2019 Michał Górny
# 2-clause BSD license

import argparse
import collections
import datetime
import email.utils
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

    @property
    def verbose(self):
        return self.css_class == 'verbose'


def result_sort_key(r):
    return (r.category, r.package, r.version, getattr(r, 'class'))


def get_results(input_paths, class_mapping, verbose, pkg_filter):
    for input_path in input_paths:
        if input_path == '-':
            input_path = sys.stdin
        checks = xml.etree.ElementTree.parse(input_path).getroot()
        for r in checks:
            r = Result(r, class_mapping)
            if r.verbose and not verbose:
                continue
            if not pkg_filter(r):
                continue
            yield r


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


def format_maint(el):
    return el.findtext('email').replace('@gentoo.org', '@g.o')


class ProjectGetter(object):
    def __init__(self, projects_xml):
        self.projects = xml.etree.ElementTree.parse(projects_xml).getroot()

    def find_projects_for_maintainer(self, m):
        for x in self.projects.findall('project'):
            members = frozenset(self[x.findtext('email')])
            if m in members:
                yield x.findtext('email')

    def __getitem__(self, k):
        for x in self.projects.findall('project'):
            if x.findtext('email') == k:
                # project members
                for m in x.findall('member'):
                    yield m.findtext('email')

                # inherited subproject members
                for sp in x.findall('subproject'):
                    if sp.get('inherit-members') == '1':
                        for m in self[sp.get('ref')]:
                            yield m


class MaintainerGetter(object):
    def __init__(self, repo):
        self.repo = repo

    def __getitem__(self, k):
        p = os.path.join(self.repo, k, 'metadata.xml')
        try:
            metadata = xml.etree.ElementTree.parse(p).getroot()
        except OSError:
            return []

        maints = [format_maint(x) for x in metadata.findall('maintainer')]
        return maints if maints else ['maintainer-needed']


def main(*args):
    p = argparse.ArgumentParser()
    # target: https://pkgcheck.readthedocs.io/en/latest/man/pkgcheck.html
    p.add_argument('-d', '--doc-uri', default='https://bit.ly/2LJlamg',
            help='Documentation URI to use for help links')
    p.add_argument('-m', '--maintainer',
            help='Filter by maintainer (dev, dev@g.o or full e-mail address)')
    p.add_argument('-o', '--output', default='-',
            help='Output HTML file ("-" for stdout)')
    p.add_argument('-p', '--projects', action='store_true',
            help='Recursively match projects whose member is maintainer')
    p.add_argument('-r', '--repo', default='/usr/portage',
            help='Repository path to get metadata.xml from')
    p.add_argument('-t', '--timestamp', default=None,
            help='Timestamp for results (git ISO8601-like UTC)')
    p.add_argument('-v', '--verbose', action='store_true',
            help='Enable verbose reports')
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

    maints = MaintainerGetter(args.repo)
    maint_filter = lambda x: True
    if args.maintainer:
        if not '@' in args.maintainer:
            args.maintainer += '@gentoo.org'
        elif args.maintainer.endswith('@g.o'):
            args.maintainer = args.maintainer.replace('@g.o', '@gentoo.org')

        match = [args.maintainer]
        if args.projects:
            projects = ProjectGetter(os.path.join(args.repo, 'metadata',
                                                  'projects.xml'))
            match.extend(
                    projects.find_projects_for_maintainer(args.maintainer))

        match = frozenset([x.replace('@gentoo.org', '@g.o') for x in match])
        maint_filter = lambda x: (bool(match.intersection(
            maints['/'.join((x.category, x.package))])))

    results = sorted(get_results(args.files, class_mapping, args.verbose,
                                 pkg_filter=maint_filter),
                     key=result_sort_key)

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
        results=deep_group(results),
        warnings=find_of_class(results, 'warn'),
        staging=find_of_class(results, 'staging'),
        errors=find_of_class(results, 'err'),
        ts=ts,
        maints=maints,
        doc_uri=args.doc_uri,
    )

    if args.output == '-':
        sys.stdout.write(out)
    else:
        with io.open(args.output, 'w', encoding='utf8') as f:
            f.write(out)


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
