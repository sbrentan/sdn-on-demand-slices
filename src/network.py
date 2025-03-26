#!/usr/bin/python3

import os
import json
import logging
import argparse
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.link import TCLink

from cli.cli import CustomCLI

# Configure logging to remove duplicate logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('mininet')
logger.setLevel(logging.INFO)
logger.propagate = False  # Disable propagation to avoid duplicate logs


class NetworkSlicingTopology(Topo):

    def __init__(self, topology_dict: dict):
        # Initialize topology
        Topo.__init__(self)

        # Create template host, switch, and link
        host_config = dict(inNamespace=True)
        
        # Create switch nodes
        for switch in topology_dict["switches"]:
            sconfig = {"dpid": switch["dpid"]}
            self.addSwitch(switch["id"], **sconfig)

        # Create host nodes
        for host in topology_dict["hosts"]:
            self.addHost(host["id"], **host_config)

        # Add links
        for link in topology_dict["links"]:
            link_config = {}
            if "bandwidth" in link:
                link_config["bw"] = link["bandwidth"]
            self.addLink(link["node1"], link["node2"], **link_config)

    def start(self):
        net = Mininet(
            topo=self,
            switch=OVSKernelSwitch,
            build=False,
            autoSetMacs=True,
            autoStaticArp=True,
            link=TCLink,
        )
        controller = RemoteController("c1", ip="127.0.0.1", port=6633)
        net.addController(controller)  # type: ignore
        net.build()
        net.start()

        # Using a custom CLI instead of the default one to add custom commands
        CustomCLI(net)
        net.stop()


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Network Slicing Topology")
    parser.add_argument("--topology-file", required=True, help="Path to the topology configuration json file")
    args = parser.parse_args()

    # Validate the topology file path
    topology_file_path = args.topology_file
    if not os.path.isfile(topology_file_path):
        raise FileNotFoundError(f"The topology file {topology_file_path} does not exist.")
    
    topology_dict = {}
    with open(topology_file_path, "r") as f:
        topology_dict = json.load(f)

    topo = NetworkSlicingTopology(topology_dict)
    topo.start()
