#!/bin/bash

cd "$(dirname "$0")/src"

module_path="$(pwd)"

export PYTHONIOENCODING=UTF-8

if [[ ":$PYTHONPATH:" != *":$module_path:"* ]]; then
    export PYTHONPATH="${PYTHONPATH:+"$PYTHONPATH:"}$module_path"
fi

# clean up logs, create if doesn't exist
mkdir -p logs
rm -rf logs/*

# Log file path with timestamp
export TZ="Europe/Rome"
timestamp=$(date +"%Y%m%d_%H%M%S")
log_file="logs/controller_$timestamp.log"

echo "Starting Ryu controller..."
sudo ovs-vsctl set-manager ptcp:6632

ryu-manager --observe-links ryu_app.py > "$log_file" 2>&1 &
# ryu_manager_pid=$!

# echo "Ryu controller started with PID: $ryu_manager_pid"

sleep 2

echo "Starting Mininet network..."
sudo python3 network.py

# echo "Stopping Ryu controller..."
# kill -9 $ryu_manager_pid

echo "Cleaning up..."
sudo mn -c 
echo "Done."