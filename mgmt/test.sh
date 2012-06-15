#!/bin/bash
set -e

usage()
{
cat << EOF
usage: $0 options

Run tests for this service.

OPTIONS:
    -h    Show this message
    -i    Run integration tests instead of unit tests
    -p PACKAGE
          The package you want to test
          (i.e. lib/user, for services/PlatformUser)
    -v VIRTUALENV
          The virtualenv you want to use for the test
          (i.e. PlatformUser, for services/PlatformUser)
EOF
}

unit=1
package_name=""
virtualenv_name=""
while getopts "hip:v:" opt;
do
	case $opt in
		h)
			usage
			exit 1
			;;
		i)
			unit=0
			;;
		p)
			package_name=$OPTARG
			;;
		v)
			virtualenv_name=$OPTARG
			;;
		?)
			usage
			exit 1
	esac
done

if [ -z "$package_name" -o -z "$virtualenv_name" ]; then
	usage
	exit 1
fi

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

. /opt/virtualenvs/${virtualenv_name}/bin/activate
# Backwards combility for projects that put code under the lib directory.
export PYTHONPATH=$PYTHONPATH:"${appdir}/lib"

cd "${appdir}"

find . -name '*.pyc' -exec rm {} \;

cmd="python $(which py.test)"
if [ $unit -eq 1 ]; then
	${cmd} --cov-report html --cov-report xml --cov-report term --cov ${package_name} ${package_name}
else
	# Support both integration test directory names.
	if [[ -d itests ]]; then
		${cmd} ./itests
	else
		${cmd} ./integration_tests
	fi
fi

deactivate

# >>> from BeautifulSoup import BeautifulSoup
# >>> soup = BeautifulSoup(open('htmlcov/index.html', 'r'))
# >>> element = soup.find('span', {'class': 'pc_cov'})
# >>> print element.text.replace('%', '')
# 69
