import logging
import os
import re
import yaml
import copy
from server_management.base.server_factory import ServerFactory
from security.security_mechanism import check_safety_feature


def merge(source, destination):
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            merge(value, node)
        else:
            destination[key] = value
    return destination


def get_ip_addresses_from_dict(data):
    addresses = []
    if not isinstance(data, dict):
        return []
    for key, value in data.items():
        if key == "nameservers":
            continue
        elif key == "addresses":
            addresses.extend([address.split("/")[0] for address in value])
        elif isinstance(value, dict):
            addresses.extend(get_ip_addresses_from_dict(value))
        elif isinstance(value, list):
            for item in value:
                addresses.extend(get_ip_addresses_from_dict(item))

    return addresses


def validate_host(host_info):
    hostname = host_info["hostname"]
    # Validates if all the servers have "address, password and user"
    if not all(
        key in host_info["management"] for key in ("address", "password", "user")
    ):
        raise ValueError(
            f"The host {hostname} doesn't have address, password, or user in management. "
            f"management: {host_info['management']}."
        )


def check_existence(path, name, is_file=True):
    full_path = os.path.join(path, name)
    exists = os.path.isfile(full_path) if is_file else os.path.isdir(full_path)
    if not exists:
        type_str = "file" if is_file else "folder"
        raise Exception(f"The {type_str} {full_path} doesn't exist")


def process_server(server_dict, role, content_servers, consolidated_info):
    safety_features = get_safety_features()
    hostname = next(iter(server_dict))
    dict_host = {}
    if "configuration" in content_servers:
        if "default" in content_servers["configuration"]:
            dict_host = copy.deepcopy(content_servers["configuration"]["default"])

        if role in content_servers["configuration"]:
            dict_host = merge(content_servers["configuration"][role], dict_host)

    if hostname in server_dict:
        dict_host = merge(server_dict[hostname], dict_host)

    dict_host["hostname"] = hostname
    if dict_host["management"]["type"] == "manual":
        logging.info(
            f"Skipping Boot Option Validation and Serial Number Obtaining for {hostname} Server."
        )
        content_servers["manual_installation"] = True
        server = None
        safety_features.remove("boot")
    else:
        validate_host(dict_host)
        server = ServerFactory.get_server(
            management_type=dict_host["management"]["type"],
            host=dict_host["management"]["address"],
            user=dict_host["management"]["user"],
            password=dict_host["management"]["password"],
            hostname=hostname,
        )
        # Gets Serial Number
        logging.info(f"Getting serial number of the host {hostname}.")
        dict_host["management"]["serial"] = server.get_serial_number()
        logging.info(f"Host {hostname}: S/N {dict_host['management']['serial']}.")

    # Extracts address of netplan configuration
    # raw_netplan
    addresses = get_ip_addresses_from_dict(
        dict_host.get("raw_netplan", {}).get("network", {})
    )
    if (
        "raw_netplan" not in dict_host
    ):  # TODO: remove when legacy netplan support is dropped
        # legacy netplan
        addresses = [
            re.findall(r"ip_address: \d+.\d+.\d+.\d+", yaml.dump(dict_host["netplan"]))[
                0
            ].split("ip_address: ")[-1]
        ]
    validated_host = check_safety_feature(server, addresses, hostname, safety_features)
    if not validated_host:
        logging.error(f"Security checks failed for host {hostname}.")
        return
    logging.info(f"Host {hostname} is validated.")
    consolidated_info.append(dict_host)


def get_safety_features():
    """
    Retrieves the list of safety features to be validated by filtering out those that are set to be skipped via the
    environment variable. It ensures that a minimum of two safety features are always checked.

    Returns:
        list: The safety features that are not skipped.
    """
    default_safety_feature = ["prometheus", "boot", "ping", "netbox"]
    skip_option_str = os.getenv("SKIP_SAFETY_FEATURE", "")
    skip_options = skip_option_str.split(",") if skip_option_str else []
    max_number_skip_options = (
        len(default_safety_feature) - 2
    )  # Minimum two features must be checked

    if len(skip_options) > max_number_skip_options:
        logging.error(
            f"Only up to {max_number_skip_options} safety features can be skipped. Attempted to skip: {skip_option_str}"
        )
        exit(1)

    # Filter out the skipped features
    return [
        feature for feature in default_safety_feature if feature not in skip_options
    ]
