from server_management.dell.dell_idrac import Idrac
from server_management.xfusion.xfusion_ibmc import Ibmc
from server_management.hp.hp_ilo import Ilo


class ServerFactory:
    @staticmethod
    def get_server(management_type, host, user, password, hostname):
        if management_type == "idrac":
            return Idrac(host, user, password, hostname)
        elif management_type == "ilo":
            return Ilo(host, user, password, hostname)
        elif management_type == "ibmc":
            return Ibmc(host, user, password, hostname)
        else:
            raise ValueError(f"Unsupported provider: {management_type}")
