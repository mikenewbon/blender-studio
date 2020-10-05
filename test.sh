#!/usr/bin/env sh
set -ux

env PYTHONPATH=. poetry run mypy .
poetry run black --check .
poetry run flake8 .
./manage.sh test
yarn run eslint .
yarn run stylelint ./**/*.scss
