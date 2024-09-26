import logging
import os
import requests
import pynetbox
from subprocess import run
from urllib.parse import urlparse


global NETBOX_URL, NETBOX_TOKEK, NETBOX_IPS

NETBOX_URL = os.environ.get("NETBOX_URL")
NETBOX_TOKEN = os.environ.get("NETBOX_TOKEN")
NETBOX_IPS = []


def _get_ips_from_netbox():
    """
    Get the list of all the IPs that are inside the Netbox Server integrated with ISO-Automator.
    This list will be used when checking the Netbox Safety Feature.

    If the NETBOX_IPs list is empty, it doesn't mean that the check is a failure; we simply return
    an empty list for the rest of the checks.
    """

    netbox_client = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)

    device_addresses = netbox_client.ipam.ip_addresses.all()

    devices = {"freeIP": set()}

    for device_address in device_addresses:
        device_interface = device_address.assigned_object
        ip_address = device_address.address.split("/")[0]

        if device_interface:
            device = str(device_interface.device)
            devices.setdefault(device, set()).add(ip_address)
        else:
            devices["freeIP"].add(ip_address)

    return devices


if NETBOX_URL and NETBOX_TOKEN:
    NETBOX_IPS = _get_ips_from_netbox()


def check_safety_feature(server, addresses, hostname, safety_features):
    """
    Validates the specified safety features of a server to ensure its readiness and compliance. Skips the features specified in safety_features.

    Parameters:
        server (Server object): The server instance to perform operations on.
        addresses (list): A list of IP addresses to check for connectivity and Prometheus security.
        hostname (str): The hostname associated with the server, used for logging.
        safety_features (list): A list of safety features that should be validated.

    Returns:
        bool: True if all enabled checks pass, False if any fail.
    """
    if "boot" in safety_features:
        logging.info(f"Starting boot options validation for host {hostname}.")
        try:
            server.check_boot_options()
        except Exception as error:
            logging.error(error)
            return False
    else:
        logging.info(
            f"Skipping boot options check for host {hostname} as per configuration."
        )

    if "ping" in safety_features:
        logging.info(f"Starting ping connectivity check for host {hostname}.")
        for address in addresses:
            if check_ping(address):
                logging.error(
                    f"Server: {hostname}, there is ping connectivity to IP {address}, skipping"
                )
                return False
    else:
        logging.info(f"Skipping ping check for host {hostname} as per configuration.")

    if "prometheus" in safety_features:
        logging.info(f"Starting Prometheus security validation for host {hostname}.")
        prometheus_url = os.environ.get("PROMETHEUS_URL")
        if prometheus_url:
            try:
                for address in addresses:
                    validate_prometheus_security(prometheus_url, address, hostname)
            except Exception as error:
                logging.error(error)
                return False
        else:
            logging.error("Prometheus URL is not set.")
            return False
    else:
        logging.info(
            f"Skipping Prometheus security check for host {hostname} as per configuration."
        )

    if "netbox" in safety_features:
        logging.info(f"Starting Netbox security validation for host {hostname}.")
        if not NETBOX_TOKEN:
            logging.error("There is not token defined for netbox.")
            return False
        if NETBOX_URL:
            try:
                validate_netbox_security(hostname, set(addresses))
            except StopIteration as error:
                logging.error(error)
                return False
        else:
            logging.error("netbox URL is not set.")
            return False
    else:
        logging.info(
            f"Skipping Netbox security check for host {hostname} as per configuration."
        )
    return True


def check_ping(address):
    logging.info(f"Checking ping to {address}")
    return (
        run(["ping", "-c", "3", address], capture_output=True, text=True).returncode
        == 0
    )


def validate_prometheus_security(prometheus_url, host_ip, hostname):
    """
    Validates that a server, which is about to have an operating system installed, is not
    sending metrics to the Prometheus server. Validation is performed using
    both the server's IP address and hostname.

    Args:
        prometheus_url (str): URL of the Prometheus server.
        host_ip (str): IP address of the host to validate.
        hostname (str): Hostname of the server to validate.

    Raises:
        Exception: If metrics are found for the host or if there is an error in the request.
    """
    # if path is not part of URL, default path is used
    if not urlparse(prometheus_url).path:
        prometheus_url = f"{prometheus_url}/api/v1/series"

    queries = [f'{{instance=~"{host_ip}(:[0-9]+)?"}}', f'{{alias="{hostname}"}}']

    # Check each match queries
    for query in queries:
        if check_metrics(query, prometheus_url):
            raise Exception(f"Error: Active metrics found for {host_ip} or {hostname}.")


def check_metrics(match_query, api_url):
    """
    Checks for the existence of metrics in Prometheus based on a given match query.

    Args:
        match_query (str): The Prometheus match expression to query.
        api_url (str): Full API URL of Prometheus to query the series.

    Returns:
        bool: True if metrics are found, False otherwise.

    Raises:
        Exception: If the HTTP request fails or returns a non-success status code.
    """
    query_params = {"match[]": match_query}
    response = requests.get(api_url, params=query_params)

    if response.status_code == 200:
        data = response.json()
        if data.get("data"):
            logging.info(f"Metrics found for the query: {match_query}")
            return True
        logging.info(f"No metrics found for the query: {match_query}")
        return False
    else:
        logging.info(f"Request error: {response.status_code} {response.text}")
        raise Exception("Prometheus server failed to reply.")


def check_netbox_hostname(netbox_client, hostname):
    """
    Check if the specified hostname already exists in the Netbox Server

    Args:
        netbox_client: pynetbox.api client that let the code interact with the Netbox server
        hostname: Hostname of the server to validate.

    Returns:
        bool: True if the server exists and is not in an "Active" or "Failed" status, False otherwise.

    Raises:
        Exception: If the netbox_client request fails or returns a non-success status code.
    """
    devices = netbox_client.dcim.devices.filter(hostname)

    try:
        device_info = next(devices.response)
    except StopIteration:
        raise StopIteration(f"There is not a server {hostname} in Netbox")

    if device_info:
        if device_info.get("status").get("label") not in ("Active", "Failed"):
            return True

    raise StopIteration(
        f"The device {hostname} status is {device_info.get('status').get('label')}. Stoping the installation"
    )


def check_netbox_ip(addresses, hostname):
    """
    Check if the addresses provided already exists in the Netbox server

    Args:
        addresses (set): Set of addresses to validate.
        hostname (str): Hostname of the server to validate.

    Returns:
        bool: True if none of the addresses exist in the Netbox server, they are associated to the same hostname
        or they are not associated to any other server in Netbox;

    Raises:
        StopIteration: The IP address already exists in the Netbox server and is associated to a different server than the
        hostname
    """
    if not NETBOX_IPS:
        logging.info(f"The server {hostname} doesn't have any IP associated")
        return True

    if addresses == NETBOX_IPS[hostname]:
        logging.info(
            f"The IPs from the ISO-Automator are the same that in Netbox for host {hostname}"
        )
        return True

    diff_ip = addresses - NETBOX_IPS[hostname]

    if not diff_ip:
        logging.info(
            f"The IPs {addresses} are a subset of the ones in Netbox for server {hostname}"
        )
        logging.warning(f"The IPs {NETBOX_IPS[hostname] - addresses} are missing !")
        return True

    servers = [key for key, ip_set in NETBOX_IPS.items() if diff_ip.issubset(ip_set)]

    if not servers:
        logging.warning(
            f"The IPs {diff_ip} aren't associated to any server in this Netbox"
        )
        return True
    elif servers == ["freeIP"]:
        logging.info(f"The IPs {diff_ip} are free")
        return True
    else:
        raise StopIteration(
            f"This IPs: {diff_ip} are duplicated ! The servers {servers} also have it associated"
        )


def validate_netbox_security(hostname, addresses):
    """
    Checks for the existence and status of the server in Netbox.

    Args:
        hostname (str): Hostname of the server to validate.
        token (str): Netbox's service Token

    Returns:
        bool: True if the server exists and is not in an "Active" or "Failed" status, False otherwise.

    Raises:
        StopIteration: If the HTTP request fails or returns a non-success status code.
    """
    netbox_client = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)

    try:
        if check_netbox_hostname(netbox_client, hostname):
            return check_netbox_ip(addresses, hostname)
    except StopIteration as error:
        raise error
    else:
        raise StopIteration(f"Stoping the installation for server {hostname}")
