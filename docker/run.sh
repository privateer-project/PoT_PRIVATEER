#!/bin/sh

  if [ "$1" = "host" ]; then
      ethtool -K eth0 tx off sg off tso off
      if [ "$2" = "1" ] || [ "$2" = "3" ]; then
          ip route add 10.1.2.0/24 via 10.1.1.2
      else
          ip route add 10.1.1.0/24 via 10.1.2.2
      fi

  elif [ "$1" = "controller" ]; then
      parameters_generation/gen_keys.sh "$2"
      sudo chmod 777 keys/ca.crt
      sudo cp controller/switch.py /home/p4/tutorials/utils/p4runtime_lib/switch.py
      sudo influxd &
      sleep 20
      influx -execute "CREATE DATABASE int_telemetry_db"
      p4c-bm2-ss --p4v 16 --p4runtime-files p4/pot.p4.p4info.txt -o p4/pot.json p4/pot.p4
      sudo python3 controller/runtimev2.py --p4info p4/pot.p4.p4info.txt --bmv2-json p4/pot.json --ssl
      sleep 20
      sudo python3 controller/collector_kafka.py -c "$2" &
  elif [ "$1" = "noPoT" ]; then
        
      sudo ip route add 10.1.2.0/24 via 10.0.$(($2 + 1)).2

      if [ "$3" = "first" ]; then
        sudo ip route add 10.1.1.0/24 via 10.0.2.3
      else
        sudo ip route add 10.1.1.0/24 via 10.0."$2".4
      fi
  else
      if [ "$2" = "script" ]; then
    # Obtenemos las IPs asignadas a eth1 y eth2
        ip_eth1=$(sudo ip -o -4 addr show eth1 | awk "{print $4}" | cut -d/ -f1)
        ip_eth2=$(sudo ip -o -4 addr show eth2 | awk "{print $4}" | cut -d/ -f1)

          
          # Verificamos que eth1 termine en .3 y eth2 en .2
        if [ "${ip_eth1##*.}" = 3 ] && [ "${ip_eth2##*.}" = 2 ]; then
            echo "-> ENTRA en el if: ip_eth1 acaba en .3 y ip_eth2 acaba en .2"
            sudo ip link set eth1 down
            sudo ip link set eth2 down
            sudo ip link set eth1 name temp_eth
            sudo ip link set eth2 name eth1
            sudo ip link set temp_eth name eth2
            sudo ip link set eth1 up
            sudo ip link set eth2 up
            echo "-> Intercambio de nombres de interfaces COMPLETADO"
        fi
      fi

      sleep 10
      sudo sysctl -w net.ipv4.ip_forward=0
      sudo chmod 777 keys/server_"$1".crt
      sudo simple_switch_grpc -i 1@eth1 -i 2@eth2 -i 3@eth0 --no-p4 --log-file logs/"$1" -- \
          --grpc-server-ssl \
          --grpc-server-cacert keys/ca.crt \
          --grpc-server-cert keys/server_"$1".crt \
          --grpc-server-key keys/server_"$1".key \
          --grpc-server-with-client-auth &
  fi

  tail -f /dev/null
  
