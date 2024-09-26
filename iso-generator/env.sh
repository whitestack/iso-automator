#!/bin/bash

ISO_INSTALLER_IMAGE="<my_repository>/iso-generator"

declare -A ISO_INSTALLER_IMAGE_VERSION_MAP=(
  ["Dockerfile.ubuntu20"]="${ISO_INSTALLER_IMAGE}-ubuntu20"
  ["Dockerfile.ubuntu22"]="${ISO_INSTALLER_IMAGE}-ubuntu22"
)
