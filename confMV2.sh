#!/bin/bash

# Create the IPIP tunnel for connectivity between MV2 and MV1
sudo ip tunnel add tun0 mode ipip remote 10.160.201.88 local 10.160.101.160
sudo ip link set tun0 up
sudo ip addr add 172.30.1.2/30 dev tun0

# Disable Reverse Path Filtering to allow asymmetric traffic on the tunnel
sudo sysctl -w net.ipv4.conf.tun0.rp_filter=0

# Enable IP forwarding
sudo sysctl -w net.ipv4.ip_forward=1

# Configure routing rules to force tunnel traffic into the container chain
sudo ip rule add iif tun0 lookup 100
sudo ip route add 10.160.101.147/32 via 10.1.1.3 table 100

echo "Configuration on MV2 completed."
