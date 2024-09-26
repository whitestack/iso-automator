import yaml
import os
import asyncio
import logging
from livefs_edit import __main__  # noqa: F401
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from server_management.base.server_factory import ServerFactory
from utils.utils_iso_automator import (
    process_server,
    check_existence,
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

    return consolidated_info


def install_iso(consolidated_info):
    # Configures virtual media and sets some boot things.
    iso_url = f"{os.environ.get('SERVER_URL')}/autoinstall.iso"
    logging.info("Sets virtual media url to iso-automator NGINX for all servers.")
    for host in consolidated_info:
        try:
            server = ServerFactory.get_server(
                management_type=host["management"]["type"],
                host=host["management"]["address"],
                user=host["management"]["user"],
                password=host["management"]["password"],
                hostname=host["hostname"],
            )
            logging.info("Removing old virtual media if it exists")
            server.eject_virtual_media()
            logging.info("Configuring UEFI mode")
            server.set_uefi_mode()
            logging.info(f"Inserting the URL {iso_url} as virtual media")
            server.insert_virtual_media(iso_url)
            logging.info("Configuring the virtual media")
            server.config_virtual_media()
        except Exception as error:
            logging.error(f"{error}")
            return
    asyncio.run(start_install(consolidated_info))


async def manage_server(host):
    hostname = host["hostname"]
    server = ServerFactory.get_server(
        management_type=host["management"]["type"],
        host=host["management"]["address"],
        user=host["management"]["user"],
        password=host["management"]["password"],
        hostname=hostname,
    )

    await server.power_on_server_after_media_config()


async def start_install(consolidated_info):
    tasks = []
    for host in consolidated_info:
        task = asyncio.create_task(manage_server(host))
        tasks.append(task)

    await asyncio.gather(*tasks)


def main():
    global ISO_IMAGE_NAME, KERNEL_FOLDER_NAME

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d %(levelname)s: %(message)s",
        datefmt="%d-%b-%y %H:%M:%S",
    )

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

    check_existence(ISO_BASE_PATH, ISO_IMAGE_NAME, is_file=True)
    check_existence(ISO_AUTOMATOR_PATH, KERNEL_FOLDER_NAME, is_file=False)
    logging.info(f"{ISO_IMAGE_NAME} exists.")

    consolidated_info = add_configuration(content_servers)
    install_iso(consolidated_info)


if __name__ == "__main__":
    main()
