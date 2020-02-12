#!/usr/bin/env sh
set -eux

cd "$(dirname $0)"
poetry run ./manage.py "$@"
