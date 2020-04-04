#!/bin/bash

here="$( cd "$( dirname $(realpath "${BASH_SOURCE[0]}") )" >/dev/null 2>&1 && pwd )"
root=$(realpath ${here}/..)

set -xeu

on_error() {
	exit_status=$?
	echo An error occurred
}

trap on_error ERR

# 1. runs of discus with all the possible options, to check for regressions
# 2. check the coding style
# 3. run the unittests
parallel -- "parallel ${root}/discus.py -- -h -c -d -s -t -g -m -k -v -r '' '-p 3'" \
	"pep8 ${root}/discus.py" \
	"python3 -m unittest ${root}/discus.py -v"
