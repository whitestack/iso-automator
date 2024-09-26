import yaml
import argparse
from int_pci import get_pci_interfaces
from int_baseboard import get_baseboard_interfaces


def read_yaml_file(file_path):
    # Read netplan
    with open(file_path, "r") as yaml_file:
        data = yaml.safe_load(yaml_file)
    return data


def write_yaml_file(data, file_path):
    with open(file_path, "w") as yaml_file:
        yaml.dump(data, yaml_file, default_flow_style=False)


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", required=True, help="Input YAML file path")
    parser.add_argument("--output", "-o", required=True, help="Output YAML file path")
    args = parser.parse_args()

    # Obtain real interface names
    baseboard_int_list = list(get_baseboard_interfaces())
    pci_int_list = list(get_pci_interfaces())

    # read netplan
    netplan = read_yaml_file(args.input)
    ethernets = netplan.get("network", {}).get("ethernets")
    bonds = netplan.get("network", {}).get("bonds")

    # Render if necessary
    if ethernets:
        templated_int_list = ethernets.get("TEMPLATED_INTERFACES", [])
        for templated_int in templated_int_list:
            # ensure that int_position is integer
            int_position = int(templated_int["interface_position"])
            if_type = templated_int.get("interface_type")
            if if_type == "pci":
                new_interface_name = pci_int_list[int_position]
            elif if_type == "baseboard":
                new_interface_name = baseboard_int_list[int_position]
            else:
                raise Exception("unknown interface type")
            ethernets[new_interface_name] = templated_int["interface_attributes"]
        if templated_int_list:
            ethernets.pop("TEMPLATED_INTERFACES")

    if bonds:
        for bond in bonds.values():
            templated_int_dict = bond.get("TEMPLATED_INTERFACES", {})
            int_position_list = templated_int_dict.get("interface_position", [])
            if_type = templated_int_dict.get("interface_type")
            bond["interfaces"] = bond.get("interfaces", [])
            for int_position in int_position_list:
                # ensure that int_position is integer
                int_position = int(int_position)
                if if_type == "pci":
                    new_interface_name = pci_int_list[int_position]
                elif if_type == "baseboard":
                    new_interface_name = baseboard_int_list[int_position]
                else:
                    raise Exception("unknown interface type")
                bond["interfaces"].append(new_interface_name)
            if templated_int_dict:
                bond.pop("TEMPLATED_INTERFACES")

    # Save modified netplan
    write_yaml_file(netplan, args.output)


if __name__ == "__main__":
    main()
