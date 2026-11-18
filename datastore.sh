#!/usr/bin/env bash
# The jobs database on the "data" branch, kept in parts.
#
#   datastore.sh pack <dir>    data/jobs.json, gzipped and cut into parts of 90 MB: <dir>/jobs.json.gz.00, .01, ...
#   datastore.sh unpack        the database of FETCH_HEAD (fetch the data branch first) into data/jobs.json
#
# Why parts: GitHub refuses a pushed file over 100 MB. On 18 Nov 2026 the gzipped database reached 100.88 MB (225,000 open jobs
# with their full texts), the push of the data branch was declined and the hourly run stopped before building the site.
# "unpack" also reads the single file jobs.json.gz that the branch held before that day.
set -euo pipefail
case "${1:-}" in
  pack)
    out="${2:?pack needs a directory}"
    gzip -9 -c data/jobs.json | split -b 94371840 -d -a 2 - "$out/jobs.json.gz."
    ls -l "$out" | awk '/jobs\.json\.gz\./ {print "  " $NF ": " $5 " bytes"}'
    ;;
  unpack)
    mkdir -p data
    parts=$(git ls-tree --name-only FETCH_HEAD | grep -E '^jobs\.json\.gz\.[0-9][0-9]$' | sort || true)
    if [ -n "$parts" ]; then
      for p in $parts; do git show "FETCH_HEAD:$p"; done | gunzip > data/jobs.json
    else
      git show FETCH_HEAD:jobs.json.gz | gunzip > data/jobs.json
    fi
    ;;
  *) echo "usage: datastore.sh pack <dir> | unpack" >&2; exit 2 ;;
esac
