import requests
from requests.auth import HTTPBasicAuth
from server_management.base.server_base import ServerBase
import logging
import time


class Idrac(ServerBase):
    def __init__(self, host, user, password, hostname):
        super().__init__(host, user, password, hostname)
        self.urls = {
            "system_info": f"https://{self.host}/redfish/v1/Systems/System.Embedded.1",
            "system_power": f"https://{self.host}/redfish/v1/Systems/System.Embedded.1/Actions"
            f"/ComputerSystem.Reset",
            "insert_virtual_media": f"https://{self.host}/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia"
            f"/CD/Actions/VirtualMedia.InsertMedia",
            "eject_virtual_media": f"https://{self.host}/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia"
            f"/CD/Actions/VirtualMedia.EjectMedia",
            "config_virtual_media": f"https://{self.host}/redfish/v1/Managers/iDRAC.Embedded.1/Actions/Oem"
            f"/EID_674_Manager.ImportSystemConfiguration",
            "boot_info": f"https://{self.host}/redfish/v1/Systems/System.Embedded.1/BootOptions",
        }

    def get_power_status(self):
        url = self.urls["system_info"]
        response = requests.get(
            url, auth=HTTPBasicAuth(self.user, self.password), verify=False
        )
        try:
            response.raise_for_status()
            status = response.json()["PowerState"]
        except requests.exceptions.HTTPError as error:
            status = error
        return status

    def get_serial_number(self):
        url = self.urls["system_info"]
        response = requests.get(
            url,
            auth=HTTPBasicAuth(self.user, self.password),
            verify=False,
        )
        response.raise_for_status()
        return response.json()["SKU"]

    def power_on(self):
        url = self.urls["system_power"]
        requests_body = {"ResetType": "On"}
        response = requests.post(
            url,
            auth=HTTPBasicAuth(self.user, self.password),
            json=requests_body,
            verify=False,
        )
        response.raise_for_status()

    def insert_virtual_media(self, iso_url):
        url = self.urls["insert_virtual_media"]
        requests_body = {"Image": f"{iso_url}"}
        response = requests.post(
            url,
            auth=HTTPBasicAuth(self.user, self.password),
            json=requests_body,
            verify=False,
        )
        response.raise_for_status()

    def eject_virtual_media(self):
        url = self.urls["eject_virtual_media"]
        requests.post(
            url, auth=HTTPBasicAuth(self.user, self.password), json={}, verify=False
        )

    def config_virtual_media(self):
        url = self.urls["config_virtual_media"]
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json;odata.metadata=minimal;charset=utf-8",
        }
        # fmt: off
        requests_body = {
            "ShareParameters": {"Target": "ALL"},
            "ImportBuffer": "<SystemConfiguration><Component FQDD=\"iDRAC.Embedded.1\"><Attribute Name=\"ServerBoot.1#BootOnce\">Enabled</Attribute><Attribute Name=\"ServerBoot.1#FirstBootDevice\">VCD-DVD</Attribute></Component></SystemConfiguration>",
        }
        # fmt: on
        response = requests.post(
            url,
            auth=HTTPBasicAuth(self.user, self.password),
            json=requests_body,
            headers=headers,
            verify=False,
        )
        response.raise_for_status()

    def __set_hdd_as_next_boot_device(self):
        url = self.urls["system_info"]
        headers = {
            "Content-Type": "application/json",
        }
        requests_body = {
            "Boot": {
                "BootSourceOverrideTarget": "Hdd",
                "BootSourceOverrideEnabled": "Continuous",
            }
        }
        response = requests.patch(
            url,
            auth=HTTPBasicAuth(self.user, self.password),
            json=requests_body,
            headers=headers,
            verify=False,
        )
        response.raise_for_status()

    def power_off(self):
        url = self.urls["system_power"]
        requests_body = {"ResetType": "ForceOff"}
        response = requests.post(
            url,
            auth=HTTPBasicAuth(self.user, self.password),
            json=requests_body,
            verify=False,
        )
        response.raise_for_status()

    async def power_on_server_after_media_config(self):
        attempts = 0
        if self.get_power_status() == "Off":
            logging.info(f"Powering on the Host: {self.hostname}")
            self.power_on()
        elif self.get_power_status() == "On":
            logging.info(f"Rebooting Host: {self.hostname}")
            self.power_off()
            while attempts < 3:
                time.sleep(60)
                if self.get_power_status() == "Off":
                    self.power_on()
                    break
                attempts += 1
        # sleep 5 minutes until the server starts booting from virtual media
        time.sleep(300)
        self.__set_hdd_as_next_boot_device()

    def check_boot_options(self):
        url = self.urls["boot_info"]
        response_json = requests.get(
            url,
            auth=HTTPBasicAuth(self.user, self.password),
            verify=False,
        ).json()
        for item in response_json["Members"]:
            url = f"https://{self.host}{item['@odata.id']}"
            response_data = requests.get(
                url,
                auth=HTTPBasicAuth(self.user, self.password),
                verify=False,
            ).json()["DisplayName"]
            if "ubuntu" in response_data.lower():
                raise Exception(
                    f"There is a ubuntu installation in Boot Option of the host {self.hostname}. UEFI Boot option: {response_data}"
                )

    def set_uefi_mode(self):
        pass
