#!/bin/bash
export CONFIG_DIR="/etc/iso-automator"
export CERT_DIR="${CONFIG_DIR}/cert"
mkdir "${CERT_DIR}"

export key_file="${CERT_DIR}/tls.key"
export crt_file="${CERT_DIR}/tls.crt"

set -e

if [ ! -f "$key_file" ] && [ ! -f "$crt_file" ]; then
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout ${key_file} -out ${crt_file} -subj "/C=PE/ST=LIMA/L=LIMA/O=Organization/CN=IsoAutomator"
  openssl dhparam -out "${CERT_DIR}/dhparam.pem" 2048
fi

#obtener la ip  para el servicio nginx
iso_ip=$(echo $SERVER_URL | cut -d '"' -f 2 | cut -d '/' -f 3 | cut -d ':' -f 1)

#reemplazar por la ip del servidor
sed -i "s/ISO_IP/$iso_ip/g" /root/nginx-cert/nginx.conf

cat /root/nginx-cert/nginx.conf

cp /root/nginx-cert/nginx.conf "${CERT_DIR}/nginx.conf"
cp /root/nginx-cert/index.html "${CONFIG_DIR}/nginx/index.html"