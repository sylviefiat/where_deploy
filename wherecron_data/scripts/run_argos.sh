#!/bin/sh
container_exists=`docker images | grep python_where`
echo $container_exists
[[ -z "$container_exists" ]] && docker build -t python_where /scripts
docker run --rm --name argos-where --net wheredeploy_default  --link wheredeploy_wheredb_1:wheredb -v /opt/docker/where_deploy/wherecron_data/scripts/export:/export -w / python_where:latest

