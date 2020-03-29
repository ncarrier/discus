#!/bin/bash

here="$( cd "$( dirname $(realpath "${BASH_SOURCE[0]}") )" >/dev/null 2>&1 && pwd )"
root=$(realpath ${here}/..)

set -xeu

on_error() {
	exit_status=$?
	echo An error occurred
}

trap on_error ERR

# simple runs of discus with all the possible options, to check for potential
# regressions

${root}/discus.py
${root}/discus.py -h
${root}/discus.py -c
${root}/discus.py -d
${root}/discus.py -p 3
${root}/discus.py -s
${root}/discus.py -t
${root}/discus.py -g
${root}/discus.py -m
${root}/discus.py -k
${root}/discus.py -v
${root}/discus.py -r

# check the coding style
pep8 ${root}/discus.py

# now run the unittests
python3 -m unittest ${root}/discus.py -v
