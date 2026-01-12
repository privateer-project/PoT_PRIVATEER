# UC2 NAT Privateer Project
## Overview
This README provides the steps required to implement UC2 using NAT Privateer configuration.

## Steps to Implement UC2
Steps to reproduce the UC2 NAT Privateer Project:

1. Tunnel for connectivity between MV1 & MV2
Since MV1 (10.160.201.88) and MV2 (10.160.101.160) are on different Layer 2 domains and require a direct link for policy routing, an IPIP tunnel was established.

### On MV1:
#### Create the tunnel interface
```bash
sudo ip tunnel add tun0 mode ipip remote 10.160.101.160 local 10.160.201.88
sudo ip link set tun0 up
sudo ip addr add 172.30.1.1/30 dev tun0
```
#### Route traffic destined to MV3 through the tunnel
```bash
sudo ip route add 10.160.101.147 via 172.30.1.2
```

### On MV2:
#### Create the tunnel interface endpoint
```bash
sudo ip tunnel add tun0 mode ipip remote 10.160.201.88 local 10.160.101.160
sudo ip link set tun0 up
sudo ip addr add 172.30.1.2/30 dev tun0
```
#### Disable Reverse Path Filter to allow asymmetric traffic on the tunnel
```bash
sudo sysctl -w net.ipv4.conf.tun0.rp_filter=0
```

2. Docker Chain Configuration
Configuring the internal routing within the containers to force the traffic flow: h1 -> ingressNode -> middle1Node -> middle2Node -> egressNode -> h2.
A prerequisite for all containers is to have IP Forwarding enabled:
```bash
sysctl -w net.ipv4.ip_forward=1
```
Static Routing Rules (Inside Containers):
h1: ip route add 10.160.101.147 via 10.1.1.2 (to ingressNode)
ingressNode: ip route add 10.160.101.147 via 10.0.1.2 dev eth2 (to middleNode1)
middleNode1: ip route add 10.160.101.147 via 10.0.2.2 dev eth2 (to middleNode2)
middleNode2: ip route add 10.160.101.147 via 10.0.3.2 (to egressNode)
egressNode: ip route add 10.160.101.147 via 10.1.2.3 dev eth2 (to h2)
h2: Uses default gateway (MV2) to exit. No IP route rule is needed.
Another configuration that was executed was to disable ICMP Redirects to prevent containers and host from marking connections as "Invalid" due to inefficient routing paths or to just display the icmp redirects when the ping was done.
Inside Containers:
```bash
sysctl -w net.ipv4.conf.all.send_redirects=0
sysctl -w net.ipv4.conf.default.send_redirects=0
sysctl -w net.ipv4.conf.eth0.send_redirects=0
```
3. Host MV2 Configuration
Configuring MV2 to intercept tunnel traffic and force it into the Docker chain.
On MV2:
A prerequisite is to have IP Forwarding enabled, as it was configured on the docker containers:
```bash
sysctl -w net.ipv4.ip_forward=1
```
Force traffic coming from the tunnel to enter the first container (h1) instead of routing directly to MV3.
#### Create a rule: If input interface is tun0, use routing table 100
```bash
sudo ip rule add iif tun0 lookup 100
```
#### Add the route to table 100 pointing to h1
```bash
sudo ip route add 10.160.101.147/32 via 10.1.1.3 table 100
```
4. Destination Return Path (MV3)
MV3 receives packets with private source IPs and needs to know how to reply.
### On MV3:
Added a static route to send traffic destined for the tunnel networks back to MV2.
#### Route for Docker networks
```bash
sudo ip route add 172.30.1.0/24 via 10.160.101.160
```
By establishing all the above commented rules and configurations, full end-to-end connectivity was achieved through the custom service Docker container chain.
