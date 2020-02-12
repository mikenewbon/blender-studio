#!/usr/bin/env sh
set -eux

env PYTHONPATH=. poetry run mypy .
poetry run black --check .
./manage.sh test
yarn run stylelint '**/*.scss'
yarn run eslint .
