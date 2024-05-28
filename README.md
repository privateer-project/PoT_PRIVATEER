# OPoT
This repository generates the needed parameters to build an OPoT system as well as deploying a Docker scenario with the required number of nodes.

To run the OPoT system:
```
./scenario-generator.sh n docker
```
Change n with the number of nodes to be deployed in the scenario. 

Parameter "docker" is optional, when included, it generates the docker scenario. If not, it will just generate the OPoT parameters.

The script will generate:
- A "config" folder with the OPoT parameters and tables structured in a json file
- A "docker" folder with the compose file that builds the Docker scenario, as well as the script that is executed in every node that runs the OPoT system
- A "keys" folder with the required certificates to send parameters from the control plane to data plane via a secure ssl channel
- A "logs" folder with logs of each node execution

To try the system in the "docker" mode:
1. Access one of the hosts in the scenario
```
docker exec -it h1 /bin/sh
```
2. From the host console, try to ping the other host (10.1.2.3)
```
ping 10.1.2.3 -c 10
```
3. To check that nodes are sending metrics access the controller console
```
docker exec -it controller /bin/bash
```
4. Access the Influx database
```
influx -database 'int_telemetry_db' -execute 'SELECT * FROM int_telemetry'
```

If the system has been deployed correctly, both host will have conectivity and metrics will be stored in the influx database

There are two "malicious" alternative scenarios to prove the non working of the system in the presence of malicious nodes.

Scenario 1 replaces an OPoT node with the malicious node and Scenario 2 intercepts traffic between two OPoT nodes. To try one of the malicious scenarios:

1. Run the script to create the scenario
```
./scenario-generator.sh n docker
```
2. Tear down the docker scenario
docker-compose down
3. Replace the three files in the malicious_node folder with the ones generated (docker-compose-big.yaml, run.sh and switches.json)
4. Start the docker scenario
```
docker-compose -f docker/docker-compose-big.yaml up -d
```

Repeat the same steps to check that host do not have connectivity and metrics stored are marked with the "dropped" flag

To delete the scenario after being deployed:
```
./destroy.sh
```
### Requirements
- Docker
- Python 3
- "numpy", "sympy" and "mpmath" python libraries


table_delete PoT.t_pot 0
table_dump PoT.t_pot 