# OPoT
This repository generates the needed parameters to build an OPoT service as well as deploying a Docker scenario with the required number of nodes (with PoT and with out PoT).

## NCSRD infrastructure
We currently have two VMs available at NCSRD for the transport network:

* 10.160.3.170

* 10.160.3.169

The API for each OPoT environment is persistent and always listening for requests.

In the case that no OPoT services are running and for the deployment of a OPoT service:
```bash
curl -X POST http://10.160.3.170:5002/run-service     -H "Content-Type: application/json"      -d '{"deploy": "PoT_Service", "NodePoT": 5, "NodeNoPoT": 2, "option": "docker”}'
```

NodePoT defines the number of nodes with PoT.

NodeNoPoT defines the number of nodes without PoT.

Once the request is done, the following will be received by the requesting entity:
```json
{
  "JWT_TOKEN": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3NjE2NDIyMzUsImV4cCI6MTc2MTcyODYzNSwiYXVkIjoiaHR0cDovL215YXBwLmNvbSIsImlzcyI6Im15YXBwIn0.A3cRbWC-ewYvCO_XdD_vDKcEHPIYAFdMjGiagy3bDMAxcRDVo5XgbFLjmEqtI_KsLB8luNwBYIBLIO0Yrciha7HMkp2fa39njHxbQ2op6t9WAjQR1UEyge2X8ogqvzqYobg44lXg1KaTW6oveVycFOsUxdYy6ZAcrQk2bki0Mr4",
  "SSSS OUTPUT": "Secret Polynomial: -12 + 24x^1 + -1x^2 + -16x^3 + 19x^4\nPublic Polynomial: 0 + -37x^1 + 7x^2 + -17x^3 + -27x^4\np 67\nx [-24  47 -52 -32  18]\ny1 [41, 18, 14, 43, 2]\ny1 with TTL [44 22 19 49  9]\ny2 [16, 5, 51, 30, 26]\nLPC [21, 37, 14, 2, 61]\n['caa675f614155587db4395eae78626bd', 'e378db5cc129623cd3f7bb08155f3b8b', '3c101526f0e37b7a5e073f95f263e005', '8c18b7a1a19e7a3a6342ab4596b94a2b', 'a379cf30c210dcb042682cdb3fbacdeb', 'd6ac40694c3116e1c996f3408daf3b62', '5057f411d5d92cf7e8947bf88054dd2b', '3c17c8d4a4c718cce45ef41ba76f9094']\nM: 128207979, s: 1, a: 0\n",
  "STATUS": "Success"
}
```
* The JWT token will permit to do the requests to the Secure Oracle in order to retrieve PoT data stored on the DLT.
* The SSSS output indicates that the OPoT parameters have been correctly handled to the different nodes across the transport network.

In order to retrieve the data from the DLT an example of the request will be the following:
```bash
curl -X GET "http://10.160.3.213:3001/api/transactions/getPoT?serviceID=57310caf-bcc4-4008-82b8-6cfa6263bbcd"      -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3NjE2NDIyMzUsImV4cCI6MTc2MTcyODYzNSwiYXVkIjoiaHR0cDovL215YXBwLmNvbSIsImlzcyI6Im15YXBwIn0.A3cRbWC-ewYvCO_XdD_vDKcEHPIYAFdMjGiagy3bDMAxcRDVo5XgbFLjmEqtI_KsLB8luNwBYIBLIO0Yrciha7HMkp2fa39njHxbQ2op6t9WAjQR1UEyge2X8ogqvzqYobg44lXg1KaTW6oveVycFOsUxdYy6ZAcrQk2bki0Mr4"      -H "Content-Type: application/json"
```
The output will be simmilar to the following:
```json
{"response":[{"_id":"6900873495fed2247c533e39","evidenceType":"PoT","dbPointer":"0xe6c1152555795b20322c4bb2bccebea162f613ea11afa8fe3342442a08a36ec2","categoryTrustSources":[{"CML":48,"Container ID":"08bb5c7a3b01","Dropped":1,"Geolocation":"10.1.2.0/24,GR,Attica,Agía Paraskeví,38.0167,23.8333,50","RND":18,"sequenceNumber":1,"serviceIndex":0,"servicePathIdentifier":55,"serviceID":"57310caf-bcc4-4008-82b8-6cfa6263bbcd","switchIP":"10.0.0.15","measurement":"int_telemetry","time":18878},{"CML":48,"Container ID":"69fbba48f779","Dropped":1,"Geolocation":"10.1.2.0/24,GR,Attica,Agía Paraskeví,38.0167,23.8333,50","RND":40,"sequenceNumber":1,"serviceIndex":0,"servicePathIdentifier":23,"serviceID":"57310caf-bcc4-4008-82b8-6cfa6263bbcd","switchIP":"10.0.0.11","measurement":"int_telemetry","time":18878},{"CML":2,"Container ID":"08bb5c7a3b01","Dropped":1,"Geolocation":"10.1.2.0/24,GR,Attica,Agía Paraskeví,38.0167,23.8333,50","RND":39,"sequenceNumber":2,"serviceIndex":0,"servicePathIdentifier":55,"serviceID":"57310caf-bcc4-4008-82b8-6cfa6263bbcd","switchIP":"10.0.0.15","measurement":"int_telemetry","time":18878},{"CML":2,"Container ID":"69fbba48f779","Dropped":1,"Geolocation":"10.1.2.0/24,GR,Attica,Agía Paraskeví,38.0167,23.8333,50","RND":61,"sequenceNumber":2,"serviceIndex":0,"servicePathIdentifier":23,"serviceID":"57310caf-bcc4-4008-82b8-6cfa6263bbcd","switchIP":"10.0.0.11","measurement":"int_telemetry","time":18878},{"CML":50,"Container ID":"08bb5c7a3b01","Dropped":1,"Geolocation":"10.1.2.0/24,GR,Attica,Agía Paraskeví,38.0167,23.8333,50","RND":20,"sequenceNumber":3,"serviceIndex":0,"servicePathIdentifier":55,"serviceID":"57310caf-bcc4-4008-82b8-6cfa6263bbcd","switchIP":"10.0.0.15","measurement":"int_telemetry","time":18878},{"CML":44,"Container ID":"69fbba48f779","Dropped":1,"Geolocation":"10.1.2.0/24,GR,Attica,Agía Paraskeví,38.0167,23.8333,50","RND":36,"sequenceNumber":3,"serviceIndex":0,"servicePathIdentifier":23,"serviceID":"57310caf-bcc4-4008-82b8-6cfa6263bbcd","switchIP":"10.0.0.11","measurement":"int_telemetry","time":18879},{"CML":46,"Container ID":"08bb5c7a3b01","Dropped":1,"Geolocation":"10.1.2.0/24,GR,Attica,Agía Paraskeví,38.0167,23.8333,50","RND":16,"sequenceNumber":4,"serviceIndex":0,"servicePathIdentifier":55,"serviceID":"57310caf-bcc4-4008-82b8-6cfa6263bbcd","switchIP":"10.0.0.15","measurement":"int_telemetry","time":18879},{"CML":5,"Container ID":"69fbba48f779","Dropped":1,"Geolocation":"10.1.2.0/24,GR,Attica,Agía Paraskeví,38.0167,23.8333,50","RND":64,"sequenceNumber":4,"serviceIndex":0,"servicePathIdentifier":23,"serviceID":"57310caf-bcc4-4008-82b8-6cfa6263bbcd","switchIP":"10.0.0.11","measurement":"int_telemetry","time":18879},{"CML":30,"Container ID":"69fbba48f779","Dropped":0,"Geolocation":"10.1.2.0/24,GR,Attica,Agía Paraskeví,38.0167,23.8333,50","RND":51,"sequenceNumber":5,"serviceIndex":4,"servicePathIdentifier":55,"serviceID":"57310caf-bcc4-4008-82b8-6cfa6263bbcd","switchIP":"10.0.0.11","measurement":"int_telemetry","time":18879},{"CML":51,"Container ID":"5686d9bd7354","Dropped":0,"Geolocation":"10.1.2.0/24,GR,Attica,Agía Paraskeví,38.0167,23.8333,50","RND":51,"sequenceNumber":5,"serviceIndex":3,"servicePathIdentifier":55,"serviceID":"57310caf-bcc4-4008-82b8-6cfa6263bbcd","switchIP":"10.0.0.12","measurement":"int_telemetry","time":18879}],"timestamp":1761642288038,"signature":"0xb116afe183404d0b2bd07a583622eaa1517037c20bc2654f5dc37e1b050617ac474efc4d87473d34bc572f00a03e4fb1700d0a38910d4420eab77cd3ccf2fe211b","dataHash":"0x9a7b7ca0685577cba4028eb7a9df5765fa5dd15faf3922c30034b2bfe24d6cc0","__v":0},{"_id":"6900872295fed2247c533e36","evidenceType":"PoT","dbPointer":"0x3c07fd20a5dbec16dc925b1d514fa6b834ddd638658d076de1110eb72285f371","categoryTrustSources":[{"CML":32,"Container ID":"69fbba48f779","Dropped":0,"Geolocation":"10.1.2.0/24,GR,Attica,Agía Paraskeví,38.0167,23.8333,50","RND":21,"sequenceNumber":0,"serviceIndex":4,"servicePathIdentifier":55,"serviceID":"57310caf-bcc4-4008-82b8-6cfa6263bbcd","switchIP":"10.0.0.11","measurement":"int_telemetry","time":0},{"CML":15,"Container ID":"5686d9bd7354","Dropped":0,"Geolocation":"10.1.2.0/24,GR,Attica,Agía Paraskeví,38.0167,23.8333,50","RND":21,"sequenceNumber":0,"serviceIndex":3,"servicePathIdentifier":55,"serviceID":"57310caf-bcc4-4008-82b8-6cfa6263bbcd","switchIP":"10.0.0.12","measurement":"int_telemetry","time":1},{"CML":19,"Container ID":"37802d247ade","Dropped":0,"Geolocation":"10.1.2.0/24,GR,Attica,Agía Paraskeví,38.0167,23.8333,50","RND":21,"sequenceNumber":0,"serviceIndex":2,"servicePathIdentifier":55,"serviceID":"57310caf-bcc4-4008-82b8-6cfa6263bbcd","switchIP":"10.0.0.13","measurement":"int_telemetry","time":3},{"CML":18,"Container ID":"b9d39ad939c3","Dropped":0,"Geolocation":"10.1.2.0/24,GR,Attica,Agía Paraskeví,38.0167,23.8333,50","RND":21,"sequenceNumber":0,"serviceIndex":1,"servicePathIdentifier":55,"serviceID":"57310caf-bcc4-4008-82b8-6cfa6263bbcd","switchIP":"10.0.0.14","measurement":"int_telemetry","time":5},{"CML":51,"Container ID":"08bb5c7a3b01","Dropped":1,"Geolocation":"10.1.2.0/24,GR,Attica,Agía Paraskeví,38.0167,23.8333,50","RND":21,"sequenceNumber":0,"serviceIndex":0,"servicePathIdentifier":55,"serviceID":"57310caf-bcc4-4008-82b8-6cfa6263bbcd","switchIP":"10.0.0.15","measurement":"int_telemetry","time":7},{"CML":56,"Container ID":"08bb5c7a3b01","Dropped":0,"Geolocation":"10.1.2.0/24,GR,Attica,Agía Paraskeví,38.0167,23.8333,50","RND":63,"sequenceNumber":0,"serviceIndex":4,"servicePathIdentifier":23,"serviceID":"57310caf-bcc4-4008-82b8-6cfa6263bbcd","switchIP":"10.0.0.15","measurement":"int_telemetry","time":8},{"CML":52,"Container ID":"b9d39ad939c3","Dropped":0,"Geolocation":"10.1.2.0/24,GR,Attica,Agía Paraskeví,38.0167,23.8333,50","RND":63,"sequenceNumber":0,"serviceIndex":3,"servicePathIdentifier":23,"serviceID":"57310caf-bcc4-4008-82b8-6cfa6263bbcd","switchIP":"10.0.0.14","measurement":"int_telemetry","time":9},{"CML":41,"Container ID":"37802d247ade","Dropped":0,"Geolocation":"10.1.2.0/24,GR,Attica,Agía Paraskeví,38.0167,23.8333,50","RND":63,"sequenceNumber":0,"serviceIndex":2,"servicePathIdentifier":23,"serviceID":"57310caf-bcc4-4008-82b8-6cfa6263bbcd","switchIP":"10.0.0.13","measurement":"int_telemetry","time":10},{"CML":10,"Container ID":"5686d9bd7354","Dropped":0,"Geolocation":"10.1.2.0/24,GR,Attica,Agía Paraskeví,38.0167,23.8333,50","RND":63,"sequenceNumber":0,"serviceIndex":1,"servicePathIdentifier":23,"serviceID":"57310caf-bcc4-4008-82b8-6cfa6263bbcd","switchIP":"10.0.0.12","measurement":"int_telemetry","time":12},{"CML":4,"Container ID":"69fbba48f779","Dropped":1,"Geolocation":"10.1.2.0/24,GR,Attica,Agía Paraskeví,38.0167,23.8333,50","RND":63,"sequenceNumber":0,"serviceIndex":0,"servicePathIdentifier":23,"serviceID":"57310caf-bcc4-4008-82b8-6cfa6263bbcd","switchIP":"10.0.0.11","measurement":"int_telemetry","time":13}],"timestamp":1761642270409,"signature":"0x5078f3a28d3cd4b3831cb296b7a17e92027f798d08cee7ce5cdb5123edad4cc47a38d9602530c21587959dc675000aed2660dce0359758427a29ac6057917bb71c","dataHash":"0x5d0e24cd781d3fa8c6674854431a51604947a962bf597e92e2c9a9814c49c948","__v":0}
```

To delete a service:
```bash
curl -X DELETE http://10.160.3.170:5002/delete-service    -H "Content-Type: application/json"      -d ‘{"deploy": “PoT_Service”}'
```

If the orchestrator decides to deploy in another environment due to LoT levels falling below the threshold, the deployment can alternatively be performed on 10.160.3.170.

When deployed, the PoT controller will return the JWT token. To request PoT parameters: (e.g.,request to the secure oracle, where the Authorization bearer will need to be changed:
```bash
curl -X GET "http://10.160.3.213:3001/api/transactions/getPoT?serviceID=57310caf-bcc4-4008-82b8-6cfa6263bbcd"      -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3NTk5MTQwNTksImV4cCI6MTc2MDAwMDQ1OSwiYXVkIjoiaHR0cDovL215YXBwLmNvbSIsImlzcyI6Im15YXBwIn0.MOlvboA7nUSP7KHFur69MY0Qg4z5dDdFHW7c_4TSQKgYYKNuxj38NqjfY0iuHZ0KNI46o-JN4AL_As6fXcSwmNEhREsKrp8aUPrlfcXVY_Ncm0yVqMj-4I5a5KRMq4lQXo36gzDqJnGi_qn1Dy7VA0dQTMqj89lqtw7l1JvROzo"      -H "Content-Type: application/json"
```


To run the OPoT system (standalone):
```
./scenario-generator_nodes.sh X Y docker
```
Change X with the number of nodes with PoT to be deployed in the scenario. 
Change Y with the number of nodes without PoT to be deployed in the scenario.

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

# Alternative scenarios

There are two "malicious" alternative scenarios to prove the non working of the system in the presence of malicious nodes.

Scenario 1 replaces an OPoT node with the malicious node and Scenario 2 intercepts traffic between two OPoT nodes. To try one of the malicious scenarios:

1. Run the script to create the scenario
```
./scenario-generator.sh n docker
```
2. Tear down the docker scenario
```
./destroy-malicious.sh
```
4. Copy the three files in the malicious_node folder (docker-compose-big.yaml to "docker" folder, run.sh to "docker" folder and switches.json to "config" folder)
5. Add execution permits to run.sh
6. Start the docker scenario
```
./scenario-generator-malicious.sh
```

Repeat the same steps to check that host do not have connectivity and metrics stored are marked with the "dropped" flag
Take into account that malicious scenarios are prepared for 4 nodes deployments, if you want to test with different node-number malicious scenarios check "alt_scenarios" folder notes

To delete the scenario after being deployed:
```
./destroy.sh
```
### Requirements
- Docker
- Python 3
- "numpy", "sympy" and "mpmath" python libraries

# Kafka commands

## To deploy kafka container

docker run --network=kafka-net --rm --name broker -p 9092:9092 -e KAFKA_BROKER_ID=1 -e KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181 -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://broker:9092 -e KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 bashj79/kafka-kraft

Create the topic:
```
./kafka-topics.sh --bootstrap-server localhost:9092 --create --topic PoT-tests --partitions 1 --replication-factor 1

```
List the topics
```
./kafka-topics.sh --bootstrap-server localhost:9092 --list
```

Consume from the topic on localhost
```
./kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic PoT-tests --from-beginning
```

### Private repository for Docker Images
https://hub.docker.com/r/mattinelorza/pot

<> table_delete PoT.t_pot 0 <> 
<> table_dump PoT.t_pot <>  




