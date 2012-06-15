#!/bin/bash
set -e

function usage {
	echo >&2 "NOTE: Call this script from the root of your techbot"
	echo >&2 ""
	echo >&2 "usage: $0 [-k] [-a application]"
	echo >&2 "    -k  Keep the virtualenv; don't destroy it, if it exists."
	echo >&2 "    -a  The virtualenv will be ${venvdir}/techbot.  This flag"
	echo >&2 "        changes the name to be ${venvdir}/(arg)."
	exit 1
}

if [[ -d /var/local/pip_download_cache ]]; then
	export PIP_DOWNLOAD_CACHE=/var/local/pip_download_cache
else
	export PIP_DOWNLOAD_CACHE=$HOME/.pip_download_cache
fi

curdir=$(cd "$(dirname "$0")";pwd)
if [[ $(basename "$curdir") == "mgmt" ]]; then
	# backwards compatible location of this file: PROJECT/mgmt
	appdir=$(cd "$curdir/..";pwd)
else
	echo "I don't know where I am."
	exit 1
fi

mktemp_cmd="mktemp -t tmp.XXXXXXXXXX"
venvdir="/opt/virtualenvs"
cfgdir="$appdir/config"
application="techbot"
destroy=true
while getopts a:hk opt; do
	case "$opt" in
		a)  application="$OPTARG";;
		h)  usage;;
		k)  destroy=false;;
		\?) usage;;
	esac
done
shift `expr $OPTIND - 1`

echo "creating virualenv $venvdir/$application"

mkdir -p "$venvdir"
cd "$venvdir"

if $destroy; then
	rm -rf $application
fi

if [ ! -e $application ]; then
	virtualenv --never-download --system-site-packages --distribute $application
fi

source $application/bin/activate

# Install ipython, into all virtualenvs.
pip install 'ipython==0.12.1'

# Install the project's requirements.
pip install --requirement "$cfgdir/requirements.all.txt"

deactivate
