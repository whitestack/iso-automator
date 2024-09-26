#!/bin/bash

VENV_DIR="venv"

export python_paths=(
  "files/"
)

function install_dependencies() {
  if [ -d "$VENV_DIR" ]; then
    source $VENV_DIR/bin/activate
  else
    apt update && DEBIAN_FRONTEND=noninteractive apt install -y python3-pip python3-venv
    # Virtual Environment
    python3 -m venv $VENV_DIR
    source $VENV_DIR/bin/activate
    # Python Dependencies
    pip3 install -r test-requirements.txt
  fi
}

function black_checker() {
  echo "Running black"
  black $1 --check --diff || BLACK_RC=$?
  echo "Finished running black"
}

function flake8_checker() {
  echo "Running flake8"
  flake8 $1 || FLAKE_RC=$?
  echo "Finished running flake8"
}

function pylint_checker() {
  echo "Running pylint"
  pylint $1 || PYLINT_RC=$?
  echo "Finished running pylint"
}

function lint_validate() {
  if (( BLACK_RC != 0 || FLAKE_RC != 0 || PYLINT_RC != 0 )); then
   echo "Linter failed!!"
   exit 1
  fi
  echo "Linter success!!"
}

install_dependencies

for path in "${python_paths[@]}"; do
  black_checker "${path}"
  flake8_checker "${path}"
  pylint_checker "${path}"
  lint_validate "${path}"
done

