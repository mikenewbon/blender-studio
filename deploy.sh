#!/bin/bash

if [ -z "$1" ]; then
    echo "Use $0 studiobeta.blender.org" >&2
    exit 1
fi
DEPLOYHOST="$1"
REMOTE_DIR="/var/www/blender-studio"
SSH_OPTS="-o ClearAllForwardings=yes -o PermitLocalCommand=no"
SSH="ssh $SSH_OPTS $DEPLOYHOST"

echo -n "Deploying to $DEPLOYHOST… "

if ! ping $DEPLOYHOST -q -c 1 -W 2 >/dev/null; then
    echo "host $DEPLOYHOST cannot be pinged, refusing to deploy." >&2
    exit 2
fi

cat <<EOT
[ping OK]

press [ENTER] to continue, Ctrl+C to abort.
EOT
read dummy

$SSH -T <<EOT
set -e
cd $REMOTE_DIR
echo "Y" | ./restart.sh
EOT
