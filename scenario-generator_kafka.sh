#!/bin/bash

# Logs folder
mkdir logs
# Config folder
mkdir config
# Keys directory
mkdir keys
# docker directory
mkdir docker

# Number of nodes as an argument
NUM_MIDDLE_NODES=$(($1-2))

# Parameter generation
python3 parameters_generation/generate_pot_params.py $1

# Script executed in nodes
if  [ -n "$2" ] && [ $2 = "docker" ]; then

	# Script content
	run='#!/bin/sh

	if [ $1 = "host" ]; then
		ethtool -K eth0 tx off sg off tso off
		if [ $2 = "1" ]; then
			ip route add 10.1.2.0/24 via 10.1.1.2
		else
			ip route add 10.1.1.0/24 via 10.1.2.2
		fi
	elif [ $1 = "controller" ]; then
        sudo pip install kafka-python
        sudo pip install confluent_kafka
		parameters_generation/gen_keys.sh $2
		sudo chmod 777 keys/ca.crt
		sudo cp controller/switch.py /home/p4/tutorials/utils/p4runtime_lib/switch.py
		sudo influxd &
		sleep 10
		influx -execute "CREATE DATABASE int_telemetry_db"
		p4c-bm2-ss --p4v 16 --p4runtime-files p4/pot.p4.p4info.txt -o p4/pot.json p4/pot.p4
		sudo python3 controller/runtimev2.py --p4info p4/pot.p4.p4info.txt --bmv2-json p4/pot.json --ssl
		sleep 20
		sudo python3 controller/collector_kafka.py -c $2 &
	else
		sleep 10
		sudo sysctl -w net.ipv4.ip_forward=0
		sudo chmod 777 keys/server_$1.crt
		sudo simple_switch_grpc -i 1@eth1 -i 2@eth2 -i 3@eth0 --no-p4 --log-file logs/$1 -- --grpc-server-ssl --grpc-server-cacert keys/ca.crt --grpc-server-cert keys/server_$1.crt --grpc-server-key keys/server_$1.key --grpc-server-with-client-auth &

	fi
	tail -f /dev/null
	'

	# Script creation
	echo "$run" > docker/run.sh

	# Change script file permission
	chmod +x docker/run.sh
	# Docker Compose file generation
    echo "version: '2'
services:
    h1:
        image: scapy
        container_name: h1
        cap_add:
        - NET_ADMIN
        privileged: true
        command: /home/p4/pot/docker/run.sh host 1
        networks:
            h1_net:
                ipv4_address: 10.1.1.3
        volumes:
        - ../:/home/p4/pot
    ingressNode:
        image: p4custom-java
        container_name: ingressNode
        cap_add:
        - NET_ADMIN
        privileged: true
        command: /home/p4/pot/docker/run.sh 11
        networks:
            h1_net:
                ipv4_address: 10.1.1.2
            ingress_net:
                ipv4_address: 10.0.1.3
            controller:
                ipv4_address: 10.0.0.11
        volumes:
        - ../:/home/p4/pot
    egressNode:
        image: p4custom-java
        container_name: egressNode
        cap_add:
        - NET_ADMIN
        privileged: true
        command: /home/p4/pot/docker/run.sh $(($NUM_MIDDLE_NODES+12))
        networks:
            zegress_net:
                ipv4_address: 10.0.$(($NUM_MIDDLE_NODES+1)).2
            zh2_net:
                ipv4_address: 10.1.2.2
            controller:
                ipv4_address: 10.0.0.$(($NUM_MIDDLE_NODES+12))
        volumes:
        - ../:/home/p4/pot
    h2:
        image: scapy
        container_name: h2
        cap_add:
        - NET_ADMIN
        privileged: true
        command: /home/p4/pot/docker/run.sh host 2
        networks:
            zh2_net:
                ipv4_address: 10.1.2.3
        volumes:
        - ../:/home/p4/pot
    controller:
        image: p4custom-java
        container_name: controller
        cap_add:
        - NET_ADMIN
        privileged: true
        command:  /home/p4/pot/docker/run.sh controller $(($NUM_MIDDLE_NODES+2))
        networks:
            controller:
                ipv4_address: 10.0.0.10
            kafka-net: 
                ipv4_address: 10.2.1.10
        volumes:
        - ../:/home/p4/pot" > docker/docker-compose-big.yaml

	# Add middle node services
    for (( i=1; i<=$NUM_MIDDLE_NODES; i++ ))
    do
    if [ $i -eq 1 ]; then
        echo "    middleNode$i:
        image: p4custom-java
        container_name: middleNode$i
        cap_add:
        - NET_ADMIN
        privileged: true
        command: /home/p4/pot/docker/run.sh $(($i+11))
        networks:
            ingress_net:
                ipv4_address: 10.0.1.2
            middle$(($i))_middle$(($i+1))_net:
                ipv4_address: 10.0.$(($i+1)).3
            controller:
                ipv4_address: 10.0.0.$(($i+11))
        volumes:
        - ../:/home/p4/pot" >> docker/docker-compose-big.yaml
    elif [ $i -eq $NUM_MIDDLE_NODES ]; then
        echo "    middleNode$i:
        image: p4custom-java
        container_name: middleNode$i
        cap_add:
        - NET_ADMIN
        privileged: true
        command: /home/p4/pot/docker/run.sh $(($i+11))
        networks:
            middle$(($i-1))_middle$(($i))_net:
                ipv4_address: 10.0.$i.2
            zegress_net:
                ipv4_address: 10.0.$(($i+1)).3
            controller:
                ipv4_address: 10.0.0.$(($i+11))
        volumes:
        - ../:/home/p4/pot" >> docker/docker-compose-big.yaml
    else
        echo "    middleNode$i:
        image: p4custom-java
        container_name: middleNode$i
        cap_add:
        - NET_ADMIN
        privileged: true
        command: /home/p4/pot/docker/run.sh $(($i+11))
        networks:
            middle$(($i-1))_middle$(($i))_net:
                ipv4_address: 10.0.$i.2
            middle$(($i))_middle$(($i+1))_net:
                ipv4_address: 10.0.$(($i+1)).3
            controller:
                ipv4_address: 10.0.0.$(($i+11))
        volumes:
        - ../:/home/p4/pot" >> docker/docker-compose-big.yaml
	fi
	done


    echo "networks:
    h1_net:
        driver: bridge
        ipam:
            driver: default
            config:
                - subnet: 10.1.1.0/24
    ingress_net:
        driver: bridge
        ipam:
            driver: default
            config:
                - subnet: 10.0.1.0/24
    zegress_net:
        driver: bridge
        ipam:
            driver: default
            config:
                - subnet: 10.0.$(($NUM_MIDDLE_NODES+1)).0/24
    zh2_net:
        driver: bridge
        ipam:
            driver: default
            config:
                - subnet: 10.1.2.0/24
    controller:
        driver: bridge
        ipam:
            driver: default
            config:
                - subnet: 10.0.0.0/24
    kafka-net:
        external: true" >> docker/docker-compose-big.yaml

    # Add middle node networks
    for (( i=1; i<=$(($NUM_MIDDLE_NODES-1)); i++ ))
    do
    echo "    middle$(($i))_middle$(($i+1))_net:
        driver: bridge
        ipam: 
            driver: default
            config:
                - subnet: 10.0.$(($i+1)).0/24" >> docker/docker-compose-big.yaml
	done

	# Scenario up
	docker-compose -f docker/docker-compose-big.yaml up -d
fi