#!/bin/bash
sudo docker-compose -f docker/docker-compose-big.yaml down
rm -rf logs/
rm -rf config/
rm -rf parameters_generation/keys/
rm -rf docker/
rm -rf keys/
rm p4/pot.json
rm p4/pot.p4.p4info.txt