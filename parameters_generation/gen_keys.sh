#!/bin/bash

NUM_IP=$(($1+10))
password=abcd

# Generate CA
openssl genrsa -passout pass:$password -des3 -out keys/ca.key 4096
openssl req -passin pass:$password -new -x509 -days 365 -key keys/ca.key -out keys/ca.crt \
  -subj "/C=US/ST=CA/L=PaloAlto/O=Test/OU=Test/CN=Root CA"

# Generate certificates and keys for servers
for ((i=11; i<=$NUM_IP; i++)); do
  # Generate server certificate and key
  openssl genrsa -passout pass:$password -des3 -out keys/server_$i.key 4096
  openssl req -passin pass:$password -new -key keys/server_$i.key -out keys/server_$i.csr \
    -subj "/C=US/ST=CA/L=PaloAlto/O=Test/OU=Server/CN=server_$i"
  openssl x509 -req -passin pass:$password \
    -extfile <(printf "subjectAltName=DNS:server_$i,IP:10.0.0.$i") \
    -days 365 -in keys/server_$i.csr -CA keys/ca.crt -CAkey keys/ca.key -set_serial 01 -out keys/server_$i.crt

  # Remove passphrase from the server key
  openssl rsa -passin pass:$password -in keys/server_$i.key -out keys/server_$i.key
done

# Remove passphrase from the server key
openssl rsa -passin pass:$password -in keys/server.key -out keys/server.key

# Generate client certificate and key
openssl genrsa -passout pass:$password -des3 -out keys/client.key 4096
openssl req -passin pass:$password -new -key keys/client.key -out keys/client.csr -subj "/C=US/ST=CA/L=PaloAlto/O=Test/OU=Client/CN=p4runtime-sh"
openssl x509 -passin pass:$password -req -days 365 -in keys/client.csr -CA keys/ca.crt -CAkey keys/ca.key -set_serial 01 -out keys/client.crt

# Remove passphrase from the client key
openssl rsa -passin pass:$password -in keys/client.key -out keys/client.key