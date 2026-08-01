#!/usr/bin/env bash
# Generates a self-signed CA + server certificate for local MQTT TLS.
# Run from the broker/ directory: ./generate-certs.sh
#
# For production, replace certs/server.crt and certs/server.key with a
# certificate issued by a real CA (or Let's Encrypt), and distribute the
# corresponding CA cert to clients instead of certs/ca.crt.

set -euo pipefail
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL="*"
cd "$(dirname "$0")"
mkdir -p certs
cd certs

DAYS=3650
CN_CA="IIoT Demo Root CA"
CN_SERVER="mosquitto"

echo "Generating CA key + certificate..."
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days $DAYS \
  -out ca.crt -subj "/CN=${CN_CA}"

echo "Generating server key + CSR..."
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/CN=${CN_SERVER}"

cat > server.ext <<EOF
subjectAltName = DNS:mosquitto,DNS:localhost,IP:127.0.0.1
EOF

echo "Signing server certificate with CA..."
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days $DAYS -sha256 -extfile server.ext

rm -f server.csr server.ext ca.srl

chmod 644 ca.crt server.crt
chmod 600 ca.key server.key

echo "Done. Certs written to broker/certs/:"
ls -la .
