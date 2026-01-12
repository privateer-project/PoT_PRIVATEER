#!/bin/bash

# Create the IPIP tunnel for connectivity between MV1 and MV2
sudo ip tunnel add tun0 mode ipip remote 10.160.101.160 local 10.160.201.88
sudo ip link set tun0 up
sudo ip addr add 172.30.1.1/30 dev tun0

# Configure the route to send traffic destined to MV3 through the tunnel
sudo ip route add 10.160.101.147 via 172.30.1.2

echo "Configuration on MV1 completed."
