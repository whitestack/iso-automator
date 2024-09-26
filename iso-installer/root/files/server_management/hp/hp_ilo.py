from hpilo import Ilo as Ilo_lib
from server_management.base.server_base import ServerBase
import logging
import time


class Ilo(ServerBase):
    def __init__(self, host, user, password, hostname):
        super().__init__(host, user, password, hostname)
        self.ilo = Ilo_lib(self.host, self.user, self.password)

    def get_power_status(self):
        return self.ilo.get_host_power_status()

    def get_serial_number(self):
        return self.ilo.get_host_data()[1]["Serial Number"]

    def power_on(self):
        self.ilo.set_host_power(host_power=True)

    def insert_virtual_media(self, iso_url):
        try:
            self.ilo.insert_virtual_media("cdrom", f"{iso_url}")
        except Exception as error:
            if "VIRTUAL_MEDIA_PRIV" in str(error):
                error_msg = (
                    f"ERROR: The user of the host {self.hostname} doesn't have the privilege "
                    "VIRTUAL_MEDIA_PRIV. This is a protection mechanism. "
                    "DO NOT ACTIVATE THIS PRIVILEGE UNLESS YOU KNOW WHAT YOU'RE DOING."
                )
            else:
                error_msg = f"ERROR: The user of the host {self.hostname}\n{str(error)}"
            raise Exception(error_msg)
        self.ilo.set_vm_status(
            device="cdrom", boot_option="boot_always", write_protect=True
        )

    def set_uefi_mode(self):
        logging.info(f"Configuring UEFI mode on the {self.hostname} server")
        if self.ilo.get_current_boot_mode() == "UEFI":
            return
        logging.info(
            f"The server {self.hostname} is not in UEFI mode. Trying to set UEFI mode."
        )
        attempts = 0
        success = False
        while attempts < 3 and not success:
            try:
                self.ilo.set_pending_boot_mode("UEFI")
                success = True
            except Exception as error:
                logging.error(error)

                if self.ilo.get_host_power_status() == "ON":
                    logging.info(f"Powering off the server {self.hostname}")
                    self.ilo.set_host_power(host_power=False)
                    logging.info("Waiting 60 seconds..")
                    time.sleep(60)

                attempts += 1
        if not success:
            raise Exception(f"The server {self.host} gets 3 attempts")

    def eject_virtual_media(self):
        pass

    def config_virtual_media(self):
        attempts = 0
        success = False
        logging.info(f"Configuring virtual media on the {self.hostname} server")

        while attempts < 3 and not success:
            try:
                self.ilo.set_one_time_boot("cdrom")
                success = True
            except Exception as error:
                logging.error(error)
                if self.ilo.get_host_power_status() == "ON":
                    logging.info(f"Powering off the server {self.hostname}")
                    self.ilo.set_host_power(host_power=False)
                    logging.info("Waiting 15 seconds..")
                    time.sleep(15)

                attempts += 1

        if not success:
            raise Exception(f"The server {self.hostname} gets 3 attempts")

    def power_off(self):
        self.ilo.set_host_power(host_power=False)

    def check_boot_options(self):
        for item in self.ilo.get_persistent_boot():
            if "ubuntu" in item:
                raise Exception(
                    f"There is a ubuntu boot in the host {self.hostname}. BOOT OPTION: {item}"
                )

    async def power_on_server_after_media_config(self):
        if self.ilo.get_host_power_status() == "OFF":
            logging.info(f"Powering on the Host: {self.hostname}")
            self.ilo.set_host_power(host_power=True)
        elif self.ilo.get_host_power_status() == "ON":
            logging.info(f"Rebooting Host: {self.hostname}")
            self.ilo.warm_boot_server()
