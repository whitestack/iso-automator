from subprocess import PIPE, Popen
import json


def get_pci_interfaces():
    dmidecode_output = (
        Popen(
            "sudo dmidecode -t slot | jc --dmidecode",
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
        if "bus_address" in line["values"] and "PCI" in line["values"]["designation"]:
            if_desig = line["values"]["designation"].split("Slot ")[-1]
            if_bus = line["values"]["bus_address"].split(".")[0]

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
            if_bus = line["businfo"].split("pci@")[1].split(".")[0]
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
    for interface in get_pci_interfaces():
        print(interface)
