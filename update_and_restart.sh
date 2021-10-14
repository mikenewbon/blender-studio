#!/bin/bash

set -e

PYTHON_BIN=/var/www/venv/bin/python
POETRY_BIN=/var/www/venv/bin/poetry
DEPLOY_USER=www-data

git pull
chown $DEPLOY_USER:$DEPLOY_USER -R .
echo "Installing dependencies"
# Just look at them go breaking teh internets:
# https://github.com/pyca/cryptography/issues/5771#issuecomment-775016788
CRYPTOGRAPHY_DONT_BUILD_RUST=1 sudo -u $DEPLOY_USER $POETRY_BIN install
sudo -u $DEPLOY_USER $PYTHON_BIN manage.py migrate --plan

read -p "Continue? [y|N]" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Applying migrations"
    sudo -u $DEPLOY_USER $PYTHON_BIN manage.py migrate
    echo "Collecting static"
    sudo -u $DEPLOY_USER $PYTHON_BIN manage.py collectstatic --no-input

    echo "Restarting services"
    systemctl restart studio.service
    systemctl restart studio-background.service
    systemctl restart meilisearch.service

    systemctl status --no-pager studio.service
    systemctl status --no-pager studio-background.service
    systemctl status --no-pager meilisearch.service
fi
