from subprocess import PIPE, Popen
import os

vgs = Popen("sudo vgs", shell=True, stdout=PIPE, stderr=PIPE).communicate()

if vgs[0].decode("UTF-8"):
    vgs_status = vgs[0].decode("UTF-8").split("\n")

    for item, vg_status in enumerate(vgs_status):
        if item != 0 and vg_status != "":
            vg_name = vg_status.split()[0]
            os.system(f"sudo vgremove {vg_name} --force")

pvs = Popen("sudo pvs", shell=True, stdout=PIPE, stderr=PIPE).communicate()

if pvs[0].decode("UTF-8"):
    pvs_status = pvs[0].decode("UTF-8").split("\n")

    for item, pv_status in enumerate(pvs_status):
        if item != 0 and pv_status != "":
            pv_name = pv_status.split()[0]
            os.system(f"sudo pvremove {pv_name} --force")

mds = Popen(
    "sudo cat /proc/mdstat | grep md", shell=True, stdout=PIPE, stderr=PIPE
).communicate()

if mds[0].decode("UTF-8"):
    mds_status = mds[0].decode("UTF-8").split("\n")

    for mds_status_item in mds_status:
        if mds_status_item != "":
            mds_name = mds_status_item.split()[0]
            os.system(f"sudo mdadm --stop {mds_name}")
            os.system(f"sudo mdadm --remove {mds_name}")
