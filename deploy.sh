#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Use $0 studio.blender.org" >&2
    exit 1
fi
DEPLOYHOST="$1"
REMOTE_DIR="/var/www/blender-studio"
SSH_OPTS="-o ClearAllForwardings=yes -o PermitLocalCommand=no"
SSH="ssh $SSH_OPTS $DEPLOYHOST"
RELEASE_BRANCH=${RELEASE_BRANCH:-production}
NEXT_RELEASE_BRANCH=${NEXT_RELEASE_BRANCH:-master}

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

git fetch --all
echo "The following commits will be pushed to ${RELEASE_BRANCH} and deployed:"
git log  --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr)%Creset' --graph  --decorate --date=relative --abbrev-commit "origin/${RELEASE_BRANCH}".."origin/${NEXT_RELEASE_BRANCH}"

cat <<EOT

press [ENTER] to continue, Ctrl+C to abort.
EOT
read dummy

echo "Pulling latest ${NEXT_RELEASE_BRANCH}.."
git checkout ${NEXT_RELEASE_BRANCH} && git pull
echo "Pulling latest ${RELEASE_BRANCH}.."
git checkout ${RELEASE_BRANCH} && git pull
echo "Fast-forwarding ${RELEASE_BRANCH} to latest changes in ${NEXT_RELEASE_BRANCH}.."
git merge --ff-only ${NEXT_RELEASE_BRANCH} && git push

# FIXME(anna): make confirmation work with the remote script instead of echoing Y into it.
$SSH -T <<EOT
set -e
cd $REMOTE_DIR
echo "Y" | ./update_and_restart.sh
EOT

echo "Done, switching back to ${NEXT_RELEASE_BRANCH}"
git checkout ${NEXT_RELEASE_BRANCH}
