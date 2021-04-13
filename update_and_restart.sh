#!/bin/bash

set -e

source /var/www/venv/bin/activate
git pull
echo "Installing dependencies"
# Just look at them go breaking teh internets:
# https://github.com/pyca/cryptography/issues/5771#issuecomment-775016788
CRYPTOGRAPHY_DONT_BUILD_RUST=1 poetry install
./manage.py migrate --plan

read -p "Continue? [y|N]" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Applying migrations"
    ./manage.py migrate
    echo "Collecting static"
    ./manage.py collectstatic --no-input
    deactivate

    echo "Restarting services"
    systemctl restart studio.service
    systemctl restart studio-background.service
    systemctl restart meilisearch.service

    systemctl status --no-pager studio.service
    systemctl status --no-pager studio-background.service
    systemctl status --no-pager meilisearch.service
fi
