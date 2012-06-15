#!/bin/bash
set -e

curdir=$(cd "$(dirname "$0")";pwd)
if [[ $(basename "$curdir") == "mgmt" ]]; then
	# backwards compatible location of this file: PROJECT/mgmt
	appdir=$(cd "$curdir/..";pwd)
elif [[ $(basename "$curdir") == "common" ]] && [[ $(basename "$(dirname "$curdir")") == "mgmt" ]]; then
	# new location, of this file: PROJECT/mgmt/common
	appdir=$(cd "$curdir/../..";pwd)
else
	echo "I don't know where I am."
	exit 1
fi

# Remove code coverage artifacts.
rm -rf ${appdir}/htmlcov
rm -f ${appdir}/.coverage

# Remove pytest artifacts.
find ${appdir} -name '__pycache__' -type d -print0 | xargs -0 rm -rf

# Remove "compiled" files.
find ${appdir} -name '*.pyc' -exec rm {} \;
