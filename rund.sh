#!/bin/bash

AlreadyRunning=$(screen -ls | grep "[0-9]*.slatoplex.*(Detached)" | wc -l)
if [ "$AlreadyRunning" == "0" ]; then
    screen -S slatoplex -d -m .env/bin/python3 src/slatoplex.py
else
    echo "slatoplex is already running"
fi
