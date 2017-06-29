#!/bin/sh
container_exists=`docker images | grep python_where`
echo $container_exists
[[ -z "$container_exists" ]] && docker build -t python_where /scripts
docker run --rm --name argos-where --net entropiedeploy_default  --link wheredeploy_wheredb_1:wheredb -v /opt/docker/where_deploy/wherecron_data/scripts/export:/export -v /opt/docker/where_deploy/wherecron_data/scripts/argos.py:/argos.py -w / -p 27:25 python_where:latest

