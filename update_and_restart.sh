#!/bin/bash

set -e

PYTHON_BIN=/var/www/venv/bin/python
DEPLOY_USER=www-data
REMOTE_DIR="/var/www/blender-studio"

sudo -u $DEPLOY_USER git pull
echo "Installing dependencies"
# Just look at them go breaking teh internets:
# https://github.com/pyca/cryptography/issues/5771#issuecomment-775016788
CRYPTOGRAPHY_DONT_BUILD_RUST=1 sudo -u $DEPLOY_USER poetry install
sudo -u $DEPLOY_USER $PYTHON_BIN manage.py migrate --plan

read -p "Continue? [y|N]" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Applying migrations"
    sudo -u $DEPLOY_USER $PYTHON_BIN manage.py migrate
    echo "Collecting static"
    sudo -u $DEPLOY_USER $PYTHON_BIN manage.py collectstatic --no-input
    chown $DEPLOY_USER:$DEPLOY_USER -R $REMOTE_DIR

    echo "Restarting services"
    systemctl restart studio.service
    systemctl restart studio-background.service
    systemctl restart meilisearch.service

    systemctl status --no-pager studio.service
    systemctl status --no-pager studio-background.service
    systemctl status --no-pager meilisearch.service
fi
