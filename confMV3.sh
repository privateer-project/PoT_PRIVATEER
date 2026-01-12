#!/bin/bash

# Configure static route for tunnel networks
sudo ip route add 172.30.1.0/24 via 10.160.101.160

echo "Configuration on MV3 completed."
