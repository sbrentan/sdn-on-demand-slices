#!/bin/bash

cd "$(dirname "$0")/src"
module_path="$(pwd)"

################### Parse `--net` argument
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --net)
            if [[ "$2" =~ ^[1-3]$ ]]; then
                net_value="$2"
                shift 2
            else
                echo "Error: Invalid value for --net. Allowed values are: 1, 2, 3."
                exit 1
            fi
            ;;
        *)
            echo "Error: Unknown argument: $1"
            exit 1
            ;;
    esac
done

if [ -z "$net_value" ]; then
    echo "Error: --net argument is required. Possible values are: 1, 2, 3."
    exit 1
fi


################### Load example folder based on `--net` argument
example_folder="examples/net_$net_value"
if [[ ! -d "$example_folder" ]]; then
    echo "Error: Directory $example_folder does not exist."
    exit 1
fi

slices_file="$module_path/$example_folder/slices.json"
topology_file="$module_path/$example_folder/topology.json"

if [[ ! -f "$slices_file" || ! -f "$topology_file" ]]; then
    echo "Error: Required files slices.json and topology.json not found in $example_folder."
    exit 1
fi


################### Prepare paths and logs before starting Ryu controller and Mininet network

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


################### Start Ryu controller and Mininet network
echo "Starting Ryu controller..."
sudo ovs-vsctl set-manager ptcp:6632

sudo env SLICES_FILE="$slices_file" ryu-manager --observe-links ryu_app.py > "$log_file" 2>&1 &

sleep 5

echo "Starting Mininet network..."
sudo python3 network.py --topology-file "$topology_file"



################### Clean up
echo "Cleaning up..."
sudo mn -c > /dev/null 2>&1
echo "Done."