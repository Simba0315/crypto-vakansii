#!/bin/sh
# Daily update: collect fresh jobs (closed ones move to the archive), then rebuild the site into ./site
set -e
cd "$(dirname "$0")"
python3 collect.py
python3 build.py
