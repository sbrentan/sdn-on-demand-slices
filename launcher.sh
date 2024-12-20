#!/bin/bash

module_path="/comnetsemu/app/sdn-on-demand-slices"
if [[ ":$PYTHONPATH:" != *":$module_path:"* ]]; then
    export PYTHONPATH="${PYTHONPATH:+"$PYTHONPATH:"}$module_path"
    echo $PYTHONPATH
fi

rm -rf logs/*

# Log file path with timestamp
export TZ="Europe/Rome"
timestamp=$(date +"%Y%m%d_%H%M%S")
log_file="logs/controller_$timestamp.log"

echo "Starting Ryu controller..."
ryu-manager --observe-links --verbose controllers/controller.py > "$log_file" 2>&1 &
ryu_manager_pid=$!

echo "Ryu controller started with PID: $ryu_manager_pid"

sleep 1

echo "Starting Mininet network..."
sudo python3 network.py

echo "Stopping Ryu controller..."
kill -9 $ryu_manager_pid

echo "Cleaning up..."
sudo mn -c 
echo "Done."