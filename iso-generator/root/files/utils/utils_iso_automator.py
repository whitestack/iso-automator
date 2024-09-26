import logging
import time
import os
import yaml
import copy
from subprocess import call, run
from jinja2 import Environment, FileSystemLoader
from pathlib import Path


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


def ansible_playbook(playbook, extra_args):
    cmd = ["ansible-playbook"]
    cmd.extend([playbook])
    if extra_args:
        cmd.extend(["-e", extra_args])
    start_time = time.time()
    ret_code = call(cmd)
    duration_time = time.time() - start_time
    logging.info(f"Done in {duration_time} secs, ret_code {ret_code}")
    return ret_code


def process_server(server_dict, role, content_servers, consolidated_info):
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

    logging.info(f"Host {hostname} is validated.")
    consolidated_info.append(dict_host)


def check_existence(path, name, is_file=True):
    full_path = os.path.join(path, name)
    exists = os.path.isfile(full_path) if is_file else os.path.isdir(full_path)
    if not exists:
        type_str = "file" if is_file else "folder"
        raise Exception(f"The {type_str} {full_path} doesn't exist")


def write_dict_to_ansible_vars(path_vars_file, consolidated_dic):
    pxe_file = open(path_vars_file, "w+")
    pxe_file.write(yaml.dump(consolidated_dic))
    pxe_file.close()


def render_jinja_template(template_file, output_file, data):
    template_loader = FileSystemLoader(searchpath="/")
    jinja_env = Environment(
        extensions=["jinja2_ansible_filters.AnsibleCoreFiltersExtension"],
        loader=template_loader,
    )
    template = jinja_env.get_template(template_file)
    rendered_template = template.render(data)
    # save yaml
    yaml_data = yaml.safe_load(rendered_template)
    with open(output_file, "w") as stream:
        yaml.safe_dump(yaml_data, stream)


def _check_deb_files_integrity(file_path):
    deb_info = run(["dpkg", "--info", str(file_path)], capture_output=True, text=True)
    return deb_info.returncode


def _check_kernel_files(version, folder_path):
    # Define the expected patterns using the provided kernel version
    file_patterns = [
        f"linux-headers-{version}-*generic_{version}-*.deb",  # Matches the "generic" files
        f"linux-headers-{version}-*_{version}-*_all.deb",  # Matches the second type (no "generic" in the filename)
        f"linux-image-unsigned-{version}-*generic_{version}-*.deb",
        f"linux-modules-{version}-*generic_{version}-*.deb",
    ]

    for pattern in file_patterns:
        matched_files = list(folder_path.glob(pattern))
        # Just one file should match the pattern
        if len(matched_files) == 1:
            # Get the path as a string
            file_path = matched_files[0].as_posix()
            if _check_deb_files_integrity(file_path) != 0:
                logging.error(f"The file {file_path} is damaged !")
                return False
        else:
            logging.error(f"No file match the pattern {pattern} !")
            return False

    logging.info(f"All the files exists for kernel v{version}")
    return True


def validate_kernel(kernel_folder):
    try:
        folder = Path(os.path.join("/etc", "iso-automator", kernel_folder))
        return _check_kernel_files(kernel_folder.strip("kernel-v"), folder)
    except FileNotFoundError as error:
        raise error
