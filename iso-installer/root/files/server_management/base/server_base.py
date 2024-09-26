from abc import ABC, abstractmethod


class ServerBase(ABC):
    def __init__(self, host, user, password, hostname):
        self.host = host
        self.hostname = hostname
        self.user = user
        self.password = password

    @abstractmethod
    def get_power_status(self):
        pass

    @abstractmethod
    def get_serial_number(self):
        pass

    @abstractmethod
    def power_on(self):
        pass

    @abstractmethod
    def power_off(self):
        pass

    @abstractmethod
    def insert_virtual_media(self, iso_url):
        pass

    @abstractmethod
    def eject_virtual_media(self):
        pass

    @abstractmethod
    def config_virtual_media(self):
        pass

    @abstractmethod
    async def power_on_server_after_media_config(self):
        pass

    @abstractmethod
    def set_uefi_mode(self):
        pass

    @abstractmethod
    def check_boot_options(self):
        pass
