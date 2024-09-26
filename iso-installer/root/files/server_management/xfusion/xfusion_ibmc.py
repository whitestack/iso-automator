import requests
import time
import logging
from server_management.base.server_base import ServerBase


class Ibmc(ServerBase):
    def __init__(self, host, user, password, hostname):
        super().__init__(host, user, password, hostname)
        self._token = None
        self.urls = {
            "system_info": f"https://{self.host}/redfish/v1/Systems/1",
            "system_power": f"https://{self.host}/redfish/v1/Systems/1/Actions/ComputerSystem.Reset",
            "system_session": f"https://{self.host}/redfish/v1/SessionService/Sessions",
            "session_task": f"https://{self.host}/redfish/v1/TaskService/Tasks/",
            "virtual_media": f"https://{self.host}/redfish/v1/Managers/1/VirtualMedia/CD/Oem/xFusion/Actions"
            f"/VirtualMedia.VmmControl",
        }

    def get_serial_number(self):
        url = self.urls["system_info"]
        requests_header = {"X-Auth-Token": self.__get_token()}
        response = requests.get(url, headers=requests_header, verify=False)
        response_json = response.json()
        return response_json["SerialNumber"]

    def __get_token(self):
        if not self._token:
            url = self.urls["system_session"]
            requests_header = {"Content-Type": "application/json"}
            requests_body = {"UserName": self.user, "Password": self.password}
            response = requests.post(
                url, json=requests_body, headers=requests_header, verify=False
            )
            response.raise_for_status()
            self._token = response.headers["X-Auth-Token"]
        return self._token

    def get_power_status(self):
        url = self.urls["system_info"]
        requests_header = {"X-Auth-Token": self.__get_token()}
        response = requests.get(url, headers=requests_header, verify=False)
        try:
            response.raise_for_status()
            response_json = response.json()
            status = response_json["PowerState"]
        except requests.exceptions.HTTPError as error:
            status = error
        return status

    def power_on(self):
        url = self.urls["system_power"]
        requests_body = {"ResetType": "On"}
        requests_header = {
            "X-Auth-Token": self.__get_token(),
            "Content-Type": "application/json",
        }
        response = requests.post(
            url, json=requests_body, headers=requests_header, verify=False
        )
        response.raise_for_status()

    def insert_virtual_media(self, iso_url):
        url = self.urls["virtual_media"]
        requests_body = {"VmmControlType": "Connect", "Image": f"{iso_url}"}
        logging.info(requests_body)
        requests_header = {
            "X-Auth-Token": self.__get_token(),
            "Content-Type": "application/json",
        }
        response = requests.post(
            url, json=requests_body, headers=requests_header, verify=False
        )
        response.raise_for_status()
        response_json = response.json()
        status = self.get_task_status(response_json["Id"])
        if not status["status"]:
            raise Exception(status["message"])

    def eject_virtual_media(self):
        url = self.urls["virtual_media"]
        requests_body = {"VmmControlType": "Disconnect"}
        token = self.__get_token()
        logging.info(token)
        requests_header = {
            "X-Auth-Token": token,
            "Content-Type": "application/json",
        }
        requests.post(url, json=requests_body, headers=requests_header, verify=False)

    def config_virtual_media(self):
        pass

    def set_uefi_mode(self):
        url = self.urls["system_info"]
        requests_header_etag = {"X-Auth-Token": self.__get_token()}
        response = requests.get(url, headers=requests_header_etag, verify=False)
        response.raise_for_status()
        etag = response.headers["etag"]
        requests_header = {
            "X-Auth-Token": self.__get_token(),
            "Content-Type": "application/json",
            "If-Match": etag,
        }
        requests_body = {
            "Boot": {
                "BootSourceOverrideTarget": "Cd",
                "BootSourceOverrideEnabled": "Once",
                "BootSourceOverrideMode": "UEFI",
            }
        }
        requests.patch(url, headers=requests_header, json=requests_body, verify=False)

    def get_task_status(self, task_id):
        url = f"{self.urls['session_task']}/{task_id}"
        requests_header = {"X-Auth-Token": self.__get_token()}
        attempts = 0
        success = False
        msg = ""
        while attempts < 100:
            time.sleep(2)
            response_json = requests.get(
                url, headers=requests_header, verify=False
            ).json()
            if response_json["Messages"]["Severity"] == "OK":
                success = True
                msg = response_json["Messages"]["Message"]
                break
            msg = response_json["Messages"]["Message"]
            attempts += 1
        return {"status": success, "message": msg}

    def power_off(self):
        url = f"https://{self.host}/redfish/v1/Systems/1/Actions/ComputerSystem.Reset"
        requests_body = {"ResetType": "ForceOff"}
        requests_header = {
            "X-Auth-Token": self.__get_token(),
            "Content-Type": "application/json",
        }
        response = requests.post(
            url, json=requests_body, headers=requests_header, verify=False
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

    def check_boot_options(self):
        pass
