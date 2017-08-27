#!/bin/bash

if [ ! -d .env ]; then
    virtualenv .env
fi
.env/bin/pip3 install websockets bencoder
