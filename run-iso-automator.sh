#!/bin/bash

REPO="<changeme>"
ISO_GENERATOR_IMAGE_NAME="${REPO}/iso-generator"
ISO_INSTALLER_IMAGE_NAME="${REPO}/iso-installer"
NGINX_IMAGE_NAME="${REPO}/nginx"
ETC='/etc'
COMMAND='/root/installer.sh'
ACTION="install-iso"
MIN_DOCKER_VERSION="20.10.0"
ISO_PATH=""
SERVERS=""

echo "========================================================="
echo "ISO-Automator"
echo "========================================================="

#Functions
version_gt() {
    test "$(printf '%s\n' "$@" | sort -V | head -n 1)" != "$1"
}

get_ubuntu_version() {
    ISO_PATH=$(get_iso_image_name)
    local mount_point="./mnt/iso"
    mkdir -p "$mount_point"
    echo "  Mounting ${ISO_PATH} to select the most appropriate iso-generator image" >&2
    sudo mount -o loop "${ISO_PATH}" "$mount_point" >/dev/null 2>&1
    local version_info=""
    local so_version=""
    if [ -f "$mount_point/.disk/info" ]; then
        version_info=$(grep 'Ubuntu' "$mount_point/.disk/info")
    fi
    sudo umount "$mount_point"
    rmdir "$mount_point"
    case "$version_info" in
        *"Ubuntu-Server 20"*)
            so_version="-ubuntu20"
            ;;
        *"Ubuntu-Server 22"*)
            so_version="-ubuntu22"
            ;;
        *)
            return 1
            ;;
    esac
    echo "  Base ISO image information: ${version_info}" >&2
    echo $so_version
    return 0
}

get_iso_image_name() {
  local yaml_file="servers.yml"
  image_name=$(grep 'image_name:' "$yaml_file" | sed 's/.*image_name: //')
  local iso_file="base_image/${image_name}"
  if [ ! -f "$iso_file" ]; then
      echo "Error: The ISO file '$iso_file' does not exist."
      return 1
  fi
  echo "  Found ${image_name} image extracted from servers.yml" >&2
  echo $iso_file
}

add_docker_repo() {
  sudo install -m 0755 -d /etc/apt/keyrings
  sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  sudo chmod a+r /etc/apt/keyrings/docker.asc

  # Add the repository to Apt sources:
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  sudo apt-get update >/dev/null 2>&1
}

deletes_docker(){
  # Deletes old versions:
  for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove $pkg; done
}

update_docker(){
  add_docker_repo
  delete_old_packages
  sudo apt-get update >/dev/null 2>&1
  sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin -y
}

run_nginx() {
  # Check if the container is already running
  if [ "$(docker ps -q -f name=iso-automator-nginx)" ]; then
    echo "Nginx container is already running."
    return 0  # Exit the function, indicating success (no need to deploy)
  fi

  # Check if ports 80 or 443 are in use
  if lsof -i:80 -i:443 | grep LISTEN; then
    echo "Ports 80 or 443 are already in use."
    return 1  # Exit the function, indicating failure (can't deploy)
  fi

  docker run \
  -d \
  --name iso-automator-nginx \
  --volume ${CONFIGDIR}/nginx:/usr/share/nginx/html \
  --volume ${CONFIGDIR}/cert/:/etc/nginx/ \
  --ports "80:80" --ports "443:443" \
  '${NGINX_IMAGE_NAME}:${TAG}'
}

run_iso_generator() {
  docker run \
  --privileged \
  --name ${CONTAINER_NAME} \
  --rm --interactive --tty \
  --env-file iso_automator_configuration.sh \
  --env SERVERS=${SERVERS} \
  --attach stdin --attach stdout --attach stderr \
  --volume ${CONFIGDIR}:/etc/iso-automator:rw \
  --volume /tmp:/tmp:rw\
  --volume ~/overlay:/overlay:rw \
  --memory 3g \
  --memory-swap -1 \
  --cap-add SYS_ADMIN \
  --env ISO-AUTOMATOR_TAG=${TAG} \
  ${ISO_GENERATOR_IMAGE_NAME}:${TAG} ${COMMAND}
}

run_iso_installer() {
  docker run \
  --env-file iso_automator_configuration.sh \
  --volume ${CONFIGDIR}:/etc/iso-automator \
  --volume /tmp:/tmp:rw \
  --env ISO-AUTOMATOR_TAG=${TAG} \
  --env SERVERS=${SERVERS} \
  --tty \
  --name iso-installer \
  --privileged \
  -i \
  --memory 3g \
  --memory-swap -1 \
  --cap-add SYS_ADMIN \
  ${ISO_INSTALLER_IMAGE_NAME}:${TAG}
}

# Params
while (( "$#" )); do
  case "$1" in
    -c|--context)
      CONTEXT=$2
      shift 2
      ;;
    --create)
      CREATE_CONFIGDIR=1
      shift 1
      ;;
    --command)
      COMMAND=$2
      shift 2
      ;;
    -d|--configdir)
      CONFIGDIR=$2
      shift 2
      ;;
    -t|--tag)
      TAG=$2
      shift 2
      ;;
    --cached)
      CACHED=1
      shift 1
      ;;
    --action)
      ACTION=$2
      shift 2
      ;;
    --servers)
      SERVERS=$2
      shift 2
    ;;
    *) # preserve positional arguments
      INSTALLER_ARGS=${INSTALLER_ARGS}${1}" "
      shift
      ;;
  esac
done

if [ -z "$TAG" ]; then
  echo "Error: The --tag flag is mandatory. Please provide a tag."
  exit 1
fi

if [ -z "${CONTEXT}" ] ; then
    CONTAINER_NAME=iso-automator
else
    CONTAINER_NAME=iso-automator-${CONTEXT}
fi

if [ -z "${CONFIGDIR}" ] ; then
    CONFIGDIR=${ETC}/${CONTAINER_NAME}
fi


# Update initial iso-automator-image
UBUNTU_VERSION=$(get_ubuntu_version) || {
    echo "Error: Unsupported SO" >&2
    exit 1
}
ISO_GENERATOR_IMAGE_NAME="${ISO_GENERATOR_IMAGE_NAME}${UBUNTU_VERSION}"
ISO_INSTALLER_IMAGE_NAME="${ISO_INSTALLER_IMAGE_NAME}${UBUNTU_VERSION}"

echo "========================================================="
echo "SUMMARY"
echo "========================================================="
echo "  CONTEXT            :" ${CONTEXT}
echo "  ISO_INSTALLER_IMAGE:" ${ISO_INSTALLER_IMAGE_NAME}:${TAG}
echo "  ISO_GENERATOR_IMAGE:" ${ISO_GENERATOR_IMAGE_NAME}:${TAG}
echo "  CONTAINER_NAME     :" ${CONTAINER_NAME}
echo "  CONFIGDIR          :" ${CONFIGDIR}
echo "  COMMAND            :" ${COMMAND}
echo "  INSTALLER_ARGS     :" ${INSTALLER_ARGS}
echo "  ACTION             :" ${ACTION}
echo "  SERVERS            :" ${SERVERS}
echo "========================================================="

if [ ! -d ${CONFIGDIR} ]; then
    if [ -z "${CREATE_CONFIGDIR}" ]; then
        echo "Error, CONFIGDIR ${CONFIGDIR} not found (provide --create to auto create)"
        exit 255
    else
        echo Creating ${CONFIGDIR}
        sudo mkdir -p ${CONFIGDIR}
    fi
fi

sudo chmod -R o+rwx ${CONFIGDIR}

docker_version=$(docker --version 2>/dev/null | awk '{print $3}')

if [ -z "$ACTION" ]; then
    run_nginx
    run_iso_generator
    run_iso_installer
elif [ "$ACTION" == "install-iso" ]; then
    run_nginx
    run_iso_installer
elif [ "$ACTION" == "generate-iso" ]; then
    run_iso_generator
else
    echo "The action doesn't exists"
    exit 1
fi
