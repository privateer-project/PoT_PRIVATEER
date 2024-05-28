#!/bin/sh

	if [ $1 = "host" ]; then
		ethtool -K eth0 tx off sg off tso off
		if [ $2 = "1" ]; then
			ip route add 10.1.2.0/24 via 10.1.1.2
		else
			ip route add 10.1.1.0/24 via 10.1.2.2
		fi
	elif [ $1 = "controller" ]; then
		parameters_generation/gen_keys.sh $2
		sudo chmod 777 keys/ca.crt
		sudo cp controller/switch.py /home/p4/tutorials/utils/p4runtime_lib/switch.py
		sudo influxd &
		sleep 10
		influx -execute "CREATE DATABASE int_telemetry_db"
		p4c-bm2-ss --p4v 16 --p4runtime-files p4/pot.p4.p4info.txt -o p4/pot.json p4/pot.p4
		sudo python3 controller/runtimev2.py --p4info p4/pot.p4.p4info.txt --bmv2-json p4/pot.json --ssl
		sleep 20
		sudo python3 controller/collector.py -c $2 &
	else
		sleep 10
		sudo sysctl -w net.ipv4.ip_forward=0
		sudo chmod 777 keys/server_$1.crt
		sudo simple_switch_grpc -i 1@eth1 -i 2@eth2 -i 3@eth0 --no-p4 --log-file logs/$1 -- --grpc-server-ssl --grpc-server-cacert keys/ca.crt --grpc-server-cert keys/server_$1.crt --grpc-server-key keys/server_$1.key --grpc-server-with-client-auth &

	fi
	tail -f /dev/null
	
