#!/bin/bash

# To connect to the database:
#    mysql -h 127.0.0.1 -u root -P 3307 -A store

set -e
set -x

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3307
NAME=storedb
TIMEFORMAT='Time elapsed: %0R seconds.'
APP_DIR=`dirname $0`
ANONIMATRON_DIR=${ANONIMATRON_DIR:-$APP_DIR/anonimatron-1.14}

#if [ ! -f "${ANONIMATRON_DIR}" ]; then
#    echo "Path to anonimatron (${ANONIMATRON_DIR}) does not point to a valid file."
#    exit 1
#fi

OPTSTRING="f:"
while getopts ${OPTSTRING} arg; do
  case ${arg} in
    f)
        echo 'f'
        BACKUP_FILE="$OPTARG"
        ;;
    :)
        echo "Usage: ANONIMATRON_DIR=./anonimatron-1.14 ./load_store_backup.sh -f path/to/wp_dump.sql.gz"
        exit 1
        ;;
    ?)
        echo "Usage: ANONIMATRON_DIR=./anonimatron-1.14 ./load_store_backup.sh -f path/to/wp_dump.sql.gz"
        exit 1
        ;;
  esac
done

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "File ${BACKUP_FILE} not found!"
    exit 1
fi


function getContainerHealth {
  docker inspect --format '{{json .State.Health.Status}}' $1
}

function waitContainer {
  while STATUS=$(getContainerHealth $1); [ "${STATUS}" != '"healthy"' ]; do
    if [ "${STATUS}" == '"unhealthy"' ]; then
      echo "Failed!"
      exit -1
    fi
    printf .
    lf=$'\n'
    sleep 1
  done
  printf "$lf"
}

function waitContainerInit {
    while ! docker logs $1 | grep -i "MySQL init process done. Ready for start up" > /dev/null; do
        sleep 1
    done
}

docker kill $NAME || true
docker rm $NAME

echo `date`" Loading $BACKUP_FILE"
time {
docker run -d \
    --health-cmd='mysqladmin ping --silent' \
    --health-interval=10s \
    --health-timeout=3s \
    --health-retries=3 \
    --health-start-period=60s \
    --name $NAME \
    -p ${MYSQL_HOST}:${MYSQL_PORT}:3306 \
    -e MYSQL_DATABASE=store -e MYSQL_ALLOW_EMPTY_PASSWORD=1 \
    -v "${PWD}/${BACKUP_FILE}":/docker-entrypoint-initdb.d/${BACKUP_FILE} \
    -it mariadb
docker stats $NAME --no-stream

waitContainer $NAME
waitContainerInit $NAME
waitContainer $NAME
}

#echo `date`" Calling anonimatron"
#time $ANONIMATRON_DIR/anonimatron.sh -config `realpath ./store_import/config.xml`
