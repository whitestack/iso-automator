from subprocess import PIPE, Popen
import json


def get_baseboard_interfaces():
    dmidecode_output = (
        Popen(
            "sudo dmidecode -t baseboard | jc --dmidecode",
            shell=True,
            stdout=PIPE,
            stderr=PIPE,
        )
        .communicate()[0]
        .decode("UTF-8")
    )

    dmidecode_dic = json.loads(dmidecode_output)

    dic_intf = []

    for line in dmidecode_dic:
        if (
            "bus_address" in line["values"]
            and "LOM" in line["values"]["reference_designation"]
        ):
            if_desig = line["values"]["reference_designation"].split("Port ")[-1]
            if_bus = line["values"]["bus_address"]

            dic_intf.append({"order": int(if_desig), "bus": if_bus})

    lshw_output = (
        Popen("sudo lshw -c network -json", shell=True, stdout=PIPE, stderr=PIPE)
        .communicate()[0]
        .decode("UTF-8")
    )

    lshw_dic = json.loads(lshw_output)

    dic_lshw_int = {}

    for line in lshw_dic:
        if "businfo" in line and "logicalname" in line:
            if_bus = line["businfo"].split("pci@")[1]
            if_name = line["logicalname"]

            if if_bus not in dic_lshw_int:
                dic_lshw_int[if_bus] = [if_name]

            else:
                dic_lshw_int[if_bus].append(if_name)

    newlist = sorted(dic_intf, key=lambda d: d["order"])

    dic_pos = {}

    count = 1
    for item in newlist:
        if item["bus"] in dic_lshw_int:
            for interface in dic_lshw_int[item["bus"]]:
                dic_pos[count] = interface
                yield interface


if __name__ == "__main__":
    for interface in get_baseboard_interfaces():
        print(interface)
