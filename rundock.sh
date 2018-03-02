#!/bin/bash

docker build -t slatoplex .
docker run --name slatoplex -p 4002:4002 --restart=unless-stopped -d slatoplex
