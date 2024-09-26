#!/usr/bin/env bash

# Starts deployer
export ANSIBLE_HOST_KEY_CHECKING=False
if [[ -z "${ANSIBLE_ENABLE_TASK_DEBUGGER}" ]]; then
  export ANSIBLE_ENABLE_TASK_DEBUGGER=True
fi

/bin/bash nginx-cert/generate-certs.sh

/usr/bin/python3 -u iso_generator.py $@
exit $?
