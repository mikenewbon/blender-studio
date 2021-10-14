#!/bin/bash

set -e

VENV_PATH=/var/www/venv
PYTHON_BIN=$VENV_PATH/bin/python
POETRY_BIN=$VENV_PATH/bin/poetry
DEPLOY_USER=www-data

git pull
chown $DEPLOY_USER:$DEPLOY_USER -R .
chown $DEPLOY_USER:$DEPLOY_USER -R $VENV_PATH
echo "Installing dependencies"
# Just look at them go breaking teh internets:
# https://github.com/pyca/cryptography/issues/5771#issuecomment-775016788
sudo -Hu $DEPLOY_USER $POETRY_BIN config virtualenvs.create false
sudo -Hu $DEPLOY_USER $POETRY_BIN config virtualenvs.in-project true
CRYPTOGRAPHY_DONT_BUILD_RUST=1 sudo -Hu $DEPLOY_USER $POETRY_BIN install
sudo -Hu $DEPLOY_USER $PYTHON_BIN manage.py migrate --plan

read -p "Continue? [y|N]" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Applying migrations"
    sudo -Hu $DEPLOY_USER $PYTHON_BIN manage.py migrate
    echo "Collecting static"
    sudo -Hu $DEPLOY_USER $PYTHON_BIN manage.py collectstatic --no-input

    echo "Restarting services"
    systemctl restart studio.service
    systemctl restart studio-background.service
    systemctl restart meilisearch.service

    systemctl status --no-pager studio.service
    systemctl status --no-pager studio-background.service
    systemctl status --no-pager meilisearch.service
fi
