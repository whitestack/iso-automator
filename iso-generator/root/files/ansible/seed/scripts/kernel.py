import sys
from bs4 import BeautifulSoup
import requests
import os

elements = sys.argv

# Revisar si se descargo
TEMP_DOWND = False

try:
    if os.system("mkdir /etc/preseed/kernel-" + elements[1]) != 0:
        raise Exception("Kernel descargado")
except Exception as error:
    print(error)
    TEMP_DOWND = True

if TEMP_DOWND is False:
    URL = "https://kernel.ubuntu.com/~kernel-ppa/mainline/" + elements[1] + "/amd64/"

    page = requests.get(URL.encode("ascii"))

    soup = BeautifulSoup(page.content, "lxml")

    all_elements = soup.find_all("a")

    for item in all_elements:
        if "linux" in item.text and "lowlatency" not in item.text:
            print(item.text)

            os.system(
                "wget "
                + URL
                + item.text
                + " -P /etc/preseed/kernel-"
                + elements[1]
                + "/"
            )
