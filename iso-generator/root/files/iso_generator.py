import shutil
import yaml
import argparse
import os
import logging
import livefs_edit
from livefs_edit import __main__  # noqa: F401
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from utils.utils_iso_automator import (
    ansible_playbook,
    write_dict_to_ansible_vars,
    render_jinja_template,
    process_server,
    validate_kernel,
)

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

ISO_AUTOMATOR_PATH = "/etc/iso-automator"
ISO_MODIFIED_PATH = f"{ISO_AUTOMATOR_PATH}/modified_image"
ISO_IMAGE_NAME = ""
KERNEL_FOLDER_NAME = ""
ISO_BASE_PATH = f"{ISO_AUTOMATOR_PATH}/base_image"
ISO_IMAGE_VERSION = os.getenv("ISO_IMAGE_VERSION")
# Default package and repository configurations
DEFAULT_PACKAGES = {
    "apt": ["hp-scripting-tools", "hponcfg", "srvadmin-idracadm8", "python3-pip"],
    "pip": ["jc"],
    "deb": [],
    "repositories": [
        "deb [trusted=yes] http://downloads.linux.hpe.com/SDR/repo/stk focal/current non-free",
        "deb [trusted=yes] http://downloads.linux.hpe.com/SDR/repo/mcp bionic/current non-free",
    ],
}


def add_configuration(content_servers):
    consolidated_info = []
    # Consolidate all the information
    servers = os.environ.get("SERVERS", "")
    if servers:
        servers = servers.split(",")
    for role in content_servers["servers"]:
        for server in content_servers["servers"][role]:
            if servers and (server not in servers):
                continue
            process_server(server, role, content_servers, consolidated_info)

    if not consolidated_info:
        logging.error("There is no content in consolidated_info.")
        exit(1)

    # find a better way of passing non-server configuration to playbooks
    dry_run_env = os.environ.get("DRY_RUN", "")
    dry_run = dry_run_env.lower() in ["true", "1", "yes"]
    consolidated_dic = {
        "host_list": consolidated_info,
        "manual_installation": (
            True if "manual_installation" in content_servers else False
        ),
        "dry_run": dry_run,
    }
    logging.warning("Starting ansible playbook !")
    logging.info("Mounts ubuntu .iso in /mnt and copies to /mnt/modified_content")
    extra_args = f"image={ISO_IMAGE_NAME} kernel={KERNEL_FOLDER_NAME}"
    ansible_error = ansible_playbook("./ansible/iso/iso-playbook.yaml", extra_args)
    if ansible_error != 0:
        logging.error("Mounts failed.")
        exit(ansible_error)

    logging.info("Modifies grub.cfg to allow automatic installation")
    write_dict_to_ansible_vars("./ansible/grub/vars/vars.yml", consolidated_dic)
    extra_args = f"iso_version={ISO_IMAGE_VERSION} image={ISO_IMAGE_NAME}"
    ansible_error = ansible_playbook("./ansible/grub/grub-playbook.yaml", extra_args)
    if ansible_error != 0:
        logging.error("Modifies grub.cfg failed.")
        exit(ansible_error)

    logging.info("Generates autoinstall.yml per host")
    write_dict_to_ansible_vars("./ansible/seed/vars/vars.yml", consolidated_dic)
    ansible_error = ansible_playbook("./ansible/seed/preseed-playbook.yaml", extra_args)
    if ansible_error != 0:
        logging.error("Generates autoinstall.yml failed.")
        exit(ansible_error)

    logging.info("Creates the autoinstall.iso in /etc/iso-automator/nginx")
    ansible_error = ansible_playbook(
        "/root/ansible/mounting/mounting-playbook.yaml", extra_args
    )
    if ansible_error != 0:
        logging.error("Creates the autoinstall.iso failed.")
        exit(ansible_error)
    return consolidated_info


def generate_iso_with_config(content_servers):
    generate_iso_with_apt(content_servers)
    consolidated_info = add_configuration(content_servers)
    return consolidated_info


def generate_iso_with_apt(content_servers):
    iso_livefs_input = f"{ISO_BASE_PATH}/{ISO_IMAGE_NAME}"
    iso_livefs_output = f"{ISO_MODIFIED_PATH}/{ISO_IMAGE_NAME}"

    if not os.path.exists(ISO_MODIFIED_PATH):
        os.makedirs(ISO_MODIFIED_PATH)

    if "packages" not in content_servers["configuration"]["default"]:
        if not os.path.exists(iso_livefs_output):
            shutil.copy2(iso_livefs_input, iso_livefs_output)
        logging.info("There are not new packages to add ...")
        logging.info("Skip ISO generation with APT ...")
        return

    # Dell repository URLs based on the ISO image version
    dell_repositories = {
        "ubuntu-20": "deb [trusted=yes] http://linux.dell.com/repo/community/openmanage/950/focal focal main",
        "ubuntu-22": "deb [trusted=yes] http://linux.dell.com/repo/community/openmanage/11010/jammy jammy main",
    }
    # User configuration from servers.yml
    user_packages = content_servers["configuration"]["default"]["packages"]
    # Prepare data for the template
    data = dict()
    for key, value in DEFAULT_PACKAGES.items():
        data[key + "_list"] = list(set(value + user_packages.get(key, [])))

    # Append the corresponding Dell repository based on the ISO version
    data["repositories_list"].append(dell_repositories[ISO_IMAGE_VERSION])

    logging.info("Generating config.j2 for livefs_editor")
    render_jinja_template("/root/templates/config.j2", "/root/config.yaml", data)

    try:
        livefs_edit.__main__.main(
            [iso_livefs_input, iso_livefs_output, "--action-yaml", "config.yaml"]
        )
    except Exception as error:
        logging.error(f"Error executing livefs-edit: {error}")
        exit(1)


def main():
    global ARGS, ISO_IMAGE_NAME, KERNEL_FOLDER_NAME

    parser = argparse.ArgumentParser(description="ISO-AUTOMATOR generator")
    parser.add_argument(
        "--iso-type",
        type=str,
        default="iso-full",
        help="Actions available: iso-deps, iso-full",
    )
    parser.add_argument(
        "--action",
        type=str,
        default="generate-iso",
        help="Actions available: generate-iso",
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d %(levelname)s: %(message)s",
        datefmt="%d-%b-%y %H:%M:%S",
    )
    ARGS = parser.parse_args()
    logging.info(f"Validating if {ISO_AUTOMATOR_PATH}/servers.yml file exists")
    if os.path.isfile(f"{ISO_AUTOMATOR_PATH}/servers.yml") is False:
        logging.error("The servers.yml file doesn't exist")
        exit(1)
    logging.info("The servers.yml file exists.")

    # Loads servers.yaml file
    with open(f"{ISO_AUTOMATOR_PATH}/servers.yml") as file:
        content_servers = yaml.load(file, Loader=yaml.FullLoader)

    ISO_IMAGE_NAME = content_servers["configuration"]["default"]["iso_options"][
        "image_name"
    ]

    KERNEL_FOLDER_NAME = f"kernel-{content_servers['configuration']['default']['kernel_options']['version']}"

    logging.info(f"Validating kernel files in the directory: {KERNEL_FOLDER_NAME}")

    if not validate_kernel(KERNEL_FOLDER_NAME):
        logging.error(
            f"Kernel files validation failed for files in the directory {KERNEL_FOLDER_NAME}"
        )
        exit(1)

    if ARGS.iso_type == "iso-deps":
        generate_iso_with_apt(content_servers)
    elif ARGS.iso_type == "iso-full":
        generate_iso_with_config(content_servers)


if __name__ == "__main__":
    main()
