#!/bin/bash

# Crea carpetas necesarias
mkdir -p logs
mkdir -p config
mkdir -p keys
mkdir -p docker

# Número de nodos
NUM_MIDDLE_NODES=$(( $1 - 2 ))
NUM_NON_POT_NODES=$2

python3 parameters_generation/generate_pot_params2.py "$1" "$2" # For PoT and No PoT scenario call generate_pot_params2.py and add a 2nd argument

# Solo si pasamos "docker" como tercer argumento, generamos el YAML y levantamos contenedores
if [ -n "$3" ] && [ "$3" = "docker" ]; then

  run='#!/bin/sh

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
        ip_eth1=$(sudo ip -o -4 addr show eth1 | awk "{print $4}" | cut -d'/' -f1)
        ip_eth2=$(sudo ip -o -4 addr show eth2 | awk "{print $4}" | cut -d'/' -f1)

          
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
  '

  # Creamos el script run.sh dentro de docker/
  echo "$run" > docker/run.sh
  chmod +x docker/run.sh


  # 1) Cabecera y primeros servicios
  echo "version: '3'
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

  h3:
    image: scapy
    container_name: h3
    cap_add:
      - NET_ADMIN
    privileged: true
    command: /home/p4/pot/docker/run.sh host 3
    networks:
      h1_net:
        ipv4_address: 10.1.1.4
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
    command: /home/p4/pot/docker/run.sh $(( $NUM_MIDDLE_NODES + 12 ))
    networks:
      zegress_net:
        ipv4_address: 10.0.$(( $NUM_MIDDLE_NODES + 1 )).2
      zh2_net:
        ipv4_address: 10.1.2.2
      controller:
        ipv4_address: 10.0.0.$(( $NUM_MIDDLE_NODES + 12 ))
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
    image: p4custom-kafka
    container_name: controller
    cap_add:
      - NET_ADMIN
    privileged: true
    command: /home/p4/pot/docker/run.sh controller $(( $NUM_MIDDLE_NODES + 2 ))
    networks:
      controller:
        ipv4_address: 10.0.0.10
      kafka-net:
        ipv4_address: 10.2.1.10
    volumes:
      - ../:/home/p4/pot
" > docker/docker-compose-big.yaml

  # 2) Bucle para añadir middleNodes
  for (( i=1; i<=$NUM_MIDDLE_NODES+$NUM_NON_POT_NODES; i++ )); do

    if [ $i -le $NUM_MIDDLE_NODES ]; then
      # Nodos middle con PoT
      if [[ $i -eq 1  && $NUM_NON_POT_NODES -gt 1 ]]; then
        # MiddleNode1 si hay mas numPots > 1
        echo "  middleNode$i:
    image: p4custom-kafka
    container_name: middleNode$i
    cap_add:
      - NET_ADMIN
    privileged: true
    command: /home/p4/pot/docker/run.sh $(( $i + 11 ))
    networks:
      ingress_net:
        ipv4_address: 10.0.1.2  # Unique IP for each node
      controller:
        ipv4_address: 10.0.0.$(( $i + 11 ))
      middle1_middle$(( $NUM_MIDDLE_NODES + 1 ))_net:
        ipv4_address: 10.0.$(( $i + 1 )).3
    volumes:
      - ../:/home/p4/pot
" >> docker/docker-compose-big.yaml
      elif [[ $i -eq 1  && $NUM_NON_POT_NODES -eq 1 ]]; then
        # MiddleNode1 si hay numPots = 1
        echo "  middleNode$i:
    image: p4custom-kafka
    container_name: middleNode$i
    cap_add:
      - NET_ADMIN
    privileged: true
    command: /home/p4/pot/docker/run.sh $(( $i + 11 ))
    networks:
      ingress_net:
        ipv4_address: 10.0.1.2  # Unique IP for each node
      controller:
        ipv4_address: 10.0.0.$(( $i + 11 ))
      middle1_middle$(( $NUM_MIDDLE_NODES + 1 ))_net:
        ipv4_address: 10.0.$(( $i + 1 )).3
    volumes:
      - ../:/home/p4/pot
" >> docker/docker-compose-big.yaml
      elif [[ $i -eq 1  ]]; then
        # MiddleNode1
        echo "  middleNode$i:
    image: p4custom-kafka
    container_name: middleNode$i
    cap_add:
      - NET_ADMIN
    privileged: true
    command: /home/p4/pot/docker/run.sh $(( $i + 11 ))
    networks:
      ingress_net:
        ipv4_address: 10.0.1.2  # Unique IP for each node
      controller:
        ipv4_address: 10.0.0.$(( $i + 11 ))
      middle1_middle$(( $i + 1 ))_net:
        ipv4_address: 10.0.$(( $i + 1 )).3
    volumes:
      - ../:/home/p4/pot
" >> docker/docker-compose-big.yaml

      elif [[ $i -eq $NUM_MIDDLE_NODES && $NUM_MIDDLE_NODES -eq 2 && $NUM_NON_POT_NODES -gt 1 ]]; then
        # Conexion nodos con PoT con los sin PoT
        echo "  middleNode$i:
    image: p4custom-kafka
    container_name: middleNode$i
    cap_add:
      - NET_ADMIN
    privileged: true
    command: /home/p4/pot/docker/run.sh $(( $i + 11 ))
    networks:
      middle$(( $i ))_middle$(( $NUM_MIDDLE_NODES + $NUM_NON_POT_NODES ))_net:
        ipv4_address: 10.0.$(( $NUM_MIDDLE_NODES + $NUM_NON_POT_NODES + 1 )).2
      zegress_net:
        ipv4_address: 10.0.$(( $i + 1 )).3
      controller:
        ipv4_address: 10.0.0.$(( $i + 11 ))
    volumes:
      - ../:/home/p4/pot
" >> docker/docker-compose-big.yaml

      elif [[ $i -eq $NUM_MIDDLE_NODES && $NUM_NON_POT_NODES -eq 0 ]]; then
        echo "  middleNode$i:
    image: p4custom-kafka
    container_name: middleNode$i
    cap_add:
      - NET_ADMIN
    privileged: true
    command: /home/p4/pot/docker/run.sh $(( $i + 11 ))
    networks:
      middle$(( $i-1 ))_middle$(( $i ))_net:
        ipv4_address: 10.0.$i.2
      zegress_net:
        ipv4_address: 10.0.$(( $i + 1 )).3
      controller:
        ipv4_address: 10.0.0.$(( $i + 11 ))
    volumes:
      - ../:/home/p4/pot
" >> docker/docker-compose-big.yaml

      elif [[ $i -eq $NUM_MIDDLE_NODES && $NUM_MIDDLE_NODES -gt 2 && $NUM_NON_POT_NODES -gt 1 ]]; then
      #Conexion nodo con PoT con egress
      echo "  middleNode$i:
    image: p4custom-kafka
    container_name: middleNode$i
    cap_add:
      - NET_ADMIN
    privileged: true
    command: /home/p4/pot/docker/run.sh $(( $i + 11 ))
    networks:
      middle$(( $i - 1 ))_middle$(( $i ))_net:
        ipv4_address: 10.0.$(( $i )).2
      zegress_net:
        ipv4_address: 10.0.$(( $i + 1 )).3
      controller:
        ipv4_address: 10.0.0.$(( $i + 11 ))
    volumes:
      - ../:/home/p4/pot
" >> docker/docker-compose-big.yaml

      elif [[ $i -eq 2  && $NUM_MIDDLE_NODES -gt 2 && $NUM_NON_POT_NODES -gt 0 ]]; then
        # MiddleNode2 igual tienes que poner script
        echo "  middleNode$i:
    image: p4custom-kafka
    container_name: middleNode$i
    cap_add:
      - NET_ADMIN
    privileged: true
    command: /home/p4/pot/docker/run.sh $(( $i + 11 )) script
    networks:
      middle$(($i))_middle$(($i+1))_net:
        ipv4_address: 10.0.$(($i+1)).3
      controller:
        ipv4_address: 10.0.0.$(($i+11))
      middle$(( $i ))_middle$(( $NUM_MIDDLE_NODES + $NUM_NON_POT_NODES ))_net:
        ipv4_address: 10.0.$(( $NUM_MIDDLE_NODES + $NUM_NON_POT_NODES + 1 )).2
    volumes:
      - ../:/home/p4/pot
" >> docker/docker-compose-big.yaml
      elif [[ $i -eq 2  && $NUM_MIDDLE_NODES -gt 2 && $NUM_NON_POT_NODES -eq 0 ]]; then
        # MiddleNode2 igual tienes que poner script
        echo "  middleNode$i:
    image: p4custom-kafka
    container_name: middleNode$i
    cap_add:
      - NET_ADMIN
    privileged: true
    command: /home/p4/pot/docker/run.sh $(( $i + 11 )) script
    networks:
      middle$(($i-1))_middle$(($i))_net:
        ipv4_address: 10.0.$(($i)).2
      controller:
        ipv4_address: 10.0.0.$(($i+11))
      middle$(($i))_middle$(($i+1))_net:
        ipv4_address: 10.0.$(($i+1)).3
    volumes:
      - ../:/home/p4/pot
" >> docker/docker-compose-big.yaml
      elif [[ $i -eq 2  && $NUM_NON_POT_NODES -eq 1 ]]; then
        # MiddleNode2 igual tienes que poner script
        echo "  middleNode$i:
    image: p4custom-kafka
    container_name: middleNode$i
    cap_add:
      - NET_ADMIN
    privileged: true
    command: /home/p4/pot/docker/run.sh $(( $i + 11 )) script
    networks:
      middle$(($i))_middle$(($i+1))_net:
        ipv4_address: 10.0.$(($i+2)).2
      zegress_net:
        ipv4_address: 10.0.$(( $i + 1 )).3
      controller:
        ipv4_address: 10.0.0.$(($i+11))
    volumes:
      - ../:/home/p4/pot
" >> docker/docker-compose-big.yaml
      elif [[ $i -eq $NUM_MIDDLE_NODES  && $NUM_NON_POT_NODES -eq 1 ]]; then
        # MiddleNode2 igual tienes que poner script
        echo "  middleNode$i:
    image: p4custom-kafka
    container_name: middleNode$i
    cap_add:
      - NET_ADMIN
    privileged: true
    command: /home/p4/pot/docker/run.sh $(( $i + 11 )) script
    networks:
      middle$(($i-1))_middle$(($i))_net:
        ipv4_address: 10.0.$(($i)).2
      zegress_net:
        ipv4_address: 10.0.$(( $i + 1 )).3
      controller:
        ipv4_address: 10.0.0.$(($i+11))
    volumes:
      - ../:/home/p4/pot
" >> docker/docker-compose-big.yaml
      else
        # Middle nodes intermedios con PoT
        echo "  middleNode$i:
    image: p4custom-kafka
    container_name: middleNode$i
    cap_add:
      - NET_ADMIN
    privileged: true
    command: /home/p4/pot/docker/run.sh $(( $i + 11 ))
    networks:
      middle$(($i-1))_middle$(($i))_net:
        ipv4_address: 10.0.$i.2
      middle$(($i))_middle$(($i+1))_net:
        ipv4_address: 10.0.$(($i+1)).3
      controller:
        ipv4_address: 10.0.0.$(($i+11))
    volumes:
      - ../:/home/p4/pot
" >> docker/docker-compose-big.yaml
      fi
    ###############NODOS SIN POT################################   
            ## Quiero que al primer nodo se le asigne el bridge del MiddleNode1 y si, no hay mas nodo sin pot se les asigna el bridge del MiddleNode2
            # Si hay mas nodos sin PoT se le asigna el siguiente bridge del MiddleNode4
            #  Al ultimo nodo se le asignará siempre el bridge del MiddleNode2 y se le asignará el bridge del anterior
            # Para el resto de nodos se le asignaran dos bridges
	        # Middle nodes without PoT (not connected to the controller)

    elif [[ $NUM_NON_POT_NODES -ge 1 ]]; then
      # Nodos sin PoT (NUM_NON_POT_NODES)
      if [[ $NUM_NON_POT_NODES -eq 1 ]]; then
        # Solo 1 nodo sin PoT
        echo "  middleNode$i:
    image: p4custom-kafka
    container_name: middleNode$i
    cap_add:
      - NET_ADMIN
    privileged: true
    command: /home/p4/pot/docker/run.sh noPoT $i first
    networks:
      middle1_middle$(( $i ))_net:
        ipv4_address: 10.0.2.4
      middle2_middle$(( $i ))_net:
        ipv4_address: 10.0.$(( $i + 1 )).3
    volumes:
      - ../:/home/p4/pot
" >> docker/docker-compose-big.yaml

      elif [[ ( $i -eq $(( $NUM_MIDDLE_NODES + 1 )) && $NUM_NON_POT_NODES -gt 1 ) ]]; then
        # Primer nodo sin PoT habiendo varios
        echo "  middleNode$i:
    image: p4custom-kafka
    container_name: middleNode$i
    cap_add:
      - NET_ADMIN
    privileged: true
    command: /home/p4/pot/docker/run.sh noPoT $i first
    networks:
      middle1_middle$(( $i ))_net:
        ipv4_address: 10.0.2.4
      middle$(( $i ))_middle$(( $i + 1 ))_net:
        ipv4_address: 10.0.$(( $i + 1 )).4
    volumes:
      - ../:/home/p4/pot
" >> docker/docker-compose-big.yaml

      elif [ $i -eq $(( $NUM_MIDDLE_NODES + $NUM_NON_POT_NODES )) ]; then
        # Último nodo sin PoT
        echo "  middleNode$i:
    image: p4custom-kafka
    container_name: middleNode$i
    cap_add:
      - NET_ADMIN
    privileged: true
    command: /home/p4/pot/docker/run.sh noPoT $i
    networks:
      middle2_middle$(( $i ))_net:
        ipv4_address: 10.0.$(( $i + 1 )).3
      middle$(( $i - 1 ))_middle$(( $i ))_net:
        ipv4_address: 10.0.$i.2
    volumes:
      - ../:/home/p4/pot
" >> docker/docker-compose-big.yaml

      else
        # Nodos sin PoT intermedios
        echo "  middleNode$i:
    image: p4custom-kafka
    container_name: middleNode$i
    cap_add:
      - NET_ADMIN
    privileged: true
    command: /home/p4/pot/docker/run.sh noPoT $i 
    networks:
      middle$(( $i - 1 ))_middle$(( $i ))_net:
        ipv4_address: 10.0.$i.2
      middle$(( $i ))_middle$(( $i + 1 ))_net:
        ipv4_address: 10.0.$(( $i + 1 )).4
    volumes:
      - ../:/home/p4/pot
" >> docker/docker-compose-big.yaml

      fi
    else
      :
    fi
  done
  

  # 3) Definición de redes (ya fuera del bloque 'services')
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
        - subnet: 10.0.$(( $NUM_MIDDLE_NODES + 1 )).0/24

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
    external: true
" >> docker/docker-compose-big.yaml

  if [[ $NUM_NON_POT_NODES -gt 0 ]]; then
  echo "  middle1_middle$(( $NUM_MIDDLE_NODES + 1 ))_net:
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: 10.0.2.0/24
" >> docker/docker-compose-big.yaml
  fi




  # PRIMER ENLACE ENTRE MIDDLE1-MIDDLE3 
  if [[ $NUM_MIDDLE_NODES -gt 2 && $NUM_NON_POT_NODES -gt 0 ]]; then
    for (( i=2; i<=$(($NUM_MIDDLE_NODES-1)); i++ ))
      do
      echo "  middle$(($i))_middle$(($i+1))_net:
    driver: bridge
    ipam: 
      driver: default
      config:
        - subnet: 10.0.$(($i+1)).0/24
" >> docker/docker-compose-big.yaml
    done
  fi


  if [[ $NUM_NON_POT_NODES -gt 0 ]]; then
  # Redes para los nodos sin PoT
    for (( i=1; i<=$NUM_NON_POT_NODES; i++ )); do
    #SI SOLO HAY UN NODO, CREO LA RED ENTRE MIDDLE2-MIDDLE3
      if [ $NUM_NON_POT_NODES -eq 1 ]; then
        echo "  middle2_middle$(( $NUM_MIDDLE_NODES + 1 ))_net:
      driver: bridge
      ipam:
        driver: default
        config:
          - subnet: 10.0.$(( $NUM_MIDDLE_NODES + 2 )).0/24
  " >> docker/docker-compose-big.yaml
      #PARA EL ULTIMO NODO
      elif [ $NUM_NON_POT_NODES -eq $i ]; then
        echo "  middle2_middle$(( i + $NUM_MIDDLE_NODES ))_net:
      driver: bridge
      ipam:
        driver: default
        config:
          - subnet: 10.0.$(( i + $NUM_MIDDLE_NODES + 1 )).0/24
  " >> docker/docker-compose-big.yaml
      #PARA LOS NODOS DE EN MEDIO
      else
        echo "  middle$(( i + NUM_MIDDLE_NODES ))_middle$(( i + NUM_MIDDLE_NODES + 1 ))_net:
      driver: bridge
      ipam:
        driver: default
        config:
          - subnet: 10.0.$(( i + NUM_MIDDLE_NODES + 1 )).0/24
  " >> docker/docker-compose-big.yaml
      fi
    done
  fi
  if [[ $NUM_NON_POT_NODES -eq 0 ]]; then
    for (( i=1; i<=$(($NUM_MIDDLE_NODES-1)); i++ ))
  do
  echo "  middle$(($i))_middle$(($i+1))_net:
      driver: bridge
      ipam: 
          driver: default
          config:
              - subnet: 10.0.$(($i+1)).0/24" >> docker/docker-compose-big.yaml
	  done
  fi

  docker-compose -f docker/docker-compose-big.yaml up -d
fi
