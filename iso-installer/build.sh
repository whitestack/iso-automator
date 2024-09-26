#!/bin/bash
# Script to build the ISO-Automator docker instance
# Allows for the following parameters: --tag/-t <myTag>

source env.sh

set -e

if [[ "$#" -eq 2 ]] && [[ "$1" == "--tag" || "$1" == "-t" ]];
then
   ISO_AUTOMATOR_RELEASE=$2
fi

for ISO_INSTALLER_DOCKER_FILE in ${!ISO_INSTALLER_IMAGE_VERSION_MAP[@]}; do
  IMAGE_NAME=${ISO_INSTALLER_IMAGE_VERSION_MAP[$ISO_INSTALLER_DOCKER_FILE]}
  cp "docker/${ISO_INSTALLER_DOCKER_FILE}" ./
  echo ""
  echo "Building ${IMAGE_NAME}:${ISO_AUTOMATOR_RELEASE}"
  docker build -f ${ISO_INSTALLER_DOCKER_FILE} \
               --build-arg ISO_AUTOMATOR_RELEASE=${ISO_AUTOMATOR_RELEASE} \
               --tag=${IMAGE_NAME}:${ISO_AUTOMATOR_RELEASE} .
done
