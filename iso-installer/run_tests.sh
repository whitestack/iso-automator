#!/bin/bash
MODULES=(
  "root/"
)
set -e
function run_linter_tests {
	echo "Running linter tests"
	CURRENT_DIR=$(pwd)
	for MODULE in ${MODULES[@]}; do
		echo $MODULE
	    cd $MODULE  && ./run_tests.sh && cd $CURRENT_DIR
	done
}

run_linter_tests