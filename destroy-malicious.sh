#!/bin/bash
sudo docker-compose -f docker/docker-compose-big.yaml down
find logs/ -mindepth 1 -delete
rm config/switches.json
find docker/ -mindepth 1 -delete
find keys/ -mindepth 1 -delete
rm p4/pot.json
rm p4/pot.p4.p4info.txt