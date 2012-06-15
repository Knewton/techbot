#!/bin/bash
set -e

function usage {
	echo >&2 "NOTE: Call this script from the root of your project"
	echo >&2 "      (e.g. cd \$KNEWTON_REPO/services/RandomNumberServer && $0)"
	echo >&2 ""
	echo >&2 "usage: $0 [-a application] [-m module]"
	echo >&2 "    -a  If the application name is FooBar, then the virtualenv"
	echo >&2 "        directory will be ${venvdir}/FooBar. This defaults to the"
	echo >&2 "        name of the folder this script lives in (e.g. $(basename "$appdir"))."
	echo >&2 "    -m  The module to lint. Defaults to {application}."
	exit 1
}

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

venvdir="/opt/virtualenvs"
application=$(basename "$appdir")
module=$application
while getopts a:m:h opt; do
	case "$opt" in
		a)  application="$OPTARG";;
		m)  module="$OPTARG";;
		h)  usage;;
		\?) usage;;
	esac
done

. ${venvdir}/${application}/bin/activate
# Backwards combility for projects that put code under the lib directory.
export PYTHONPATH=$PYTHONPATH:"${appdir}/lib"

cd "${appdir}"

# Check that pylint is installed
pylint_cmd=$(which pylint)
if [ -z $pylint_cmd ]; then
	echo "pylint must be installed (\"sudo pip install pylint==0.25.1\")"
	exit 1
fi

# Run pylint, writing output to pylint.log and stdout
python ${pylint_cmd} --rcfile="${curdir}/.pylintrc" ${module} | tee "${appdir}/pylint.log"

deactivate
