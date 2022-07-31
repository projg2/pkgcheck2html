Syncing with new pkgcheck keywords:
1. `./update-config.py pkgcheck2html.conf.json`
2. Review `git diff pkgcheck2html.conf.json` and modify as needed.

Updating the exception list, say, for a new keyword `UnquotedVariable`:
1. `pkgcheck scan -k UnquotedVariable -R XmlReporter > /tmp/unquoted`
2. `./pkgcheck2excludes.py -c UnquotedVariable -o excludes.json /tmp/unquoted`
