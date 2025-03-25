#!/usr/bin/python3
from typing import Dict

import time
import requests
import threading
from mininet.log import setLogLevel, output
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.cli import CLI
from mininet.link import TCLink

from common.paths import ApiPaths
from common.constants import DEBUG, CONTROLLER_IP, CONTROLLER_PORT
from bandwidth_tests import BandwidthTest
import logging

# Configure logging to remove duplicate logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('mininet')
logger.setLevel(logging.INFO)
logger.propagate = False  # Disable propagation to avoid duplicate logs

stopping_flag = threading.Event()


class NetworkSlicingTopology(Topo):

    def __init__(self):
        # Initialize topology
        Topo.__init__(self)

        # Create template host, switch, and link
        host_config = dict(inNamespace=True)
        http_link_config = dict(bw=1)
        video_link_config = dict(bw=10)
        host_link_config = dict()

        # Create switch nodes
        for i in range(4):
            sconfig = {"dpid": "%016x" % (i + 1)}
            self.addSwitch("s%d" % (i + 1), **sconfig)

        # Create host nodes
        for i in range(4):
            self.addHost("h%d" % (i + 1), **host_config)

        # Add switch links
        self.addLink("s1", "s2", **video_link_config)
        self.addLink("s2", "s4", **video_link_config)
        self.addLink("s1", "s3", **http_link_config)
        self.addLink("s3", "s4", **http_link_config)

        # Add host links
        self.addLink("h1", "s1", **host_link_config)
        self.addLink("h2", "s1", **host_link_config)
        self.addLink("h3", "s4", **host_link_config)
        self.addLink("h4", "s4", **host_link_config)

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
        if DEBUG:
            print("Network started, waiting for queues to be built...")
            time.sleep(30)
            print("Trying to ping all hosts...")
            net.pingAll()

        # Using a custom CLI instead of the default one to add custom commands
        CustomCLI(net)
        net.stop()


class CustomCLI(CLI):

    """A custom CLI to add new commands."""
    first_cmd = True

    def preloop(self):
        """Executed before entering the CLI loop."""
        if self.first_cmd:
            self.first_cmd = False
            self.wait_for_nodes()

            # Start thread polling apis for packets requests
            self.polling_thread = threading.Thread(target=poll_apis_for_packets, args=({"mn": self.mn, "cli": self},))
            self.polling_thread.start()

    def postloop(self):
        if self.polling_thread.is_alive():
            stopping_flag.set()
            self.polling_thread.join()
        return super().postloop()

    def wait_for_nodes(self):
        """Wait until all nodes are correctly set up and available."""
        output("\nWaiting for all nodes to be correctly set up and available...\n")
        i = 0
        ready = False
        while i < 5:
            if i:
                # Move the cursor up and clear the line
                output("\033[A")  # Move cursor up
                output("\033[K")  # Clear line
            output(f"Attempt {i + 1}/5...\n")

            # Avoid printing output in the console
            setLogLevel("critical")
            if self.mn.ping(timeout="0.3") == 0:  # timeout is in seconds
                ready = True
                break
            setLogLevel()
            time.sleep(2)
            i += 1
        setLogLevel()
        if not ready:
            output("Some nodes are not ready. Please check the network setup.\n")
        else:
            output("All nodes are ready.\n\n")

    def do_bwtest(self, line):
        """
        Custom command to perform bandwidth tests.
        Usage: bwtest <test_id>
        """
        valid_test_ids = BandwidthTest.get_test_ids()
        test_id = line.strip()
        if not test_id or not test_id.isdigit():
            output(f"Please provide a valid test ID from {valid_test_ids}\n")
            return
        output("Performing bandwidth test %s...\n" % test_id)
        BandwidthTest.run_test(test_id, self.mn, line)
        return

    def do_reset(self, line):
        """Custom command to reset the network flows and queues."""
        output("Resetting network flows and queues...\n")
        # TODO: use constants
        # rest api query to reset network
        result = requests.post(f"http://{CONTROLLER_IP}:{CONTROLLER_PORT}{ApiPaths.RESET_SLICES()}")
        if result.status_code != 204 and result.status_code != 200:
            output("Error resetting network flows and queues\n")
            return
        output("Network flows and queues reset successfully\n")
        return
    
    def do_trace(self, line):
        """
        Custom command to trace a packet.
        Usage: trace <protocol> 
        """
        # TODO: add more params and logs
        protocol = line.strip()
        if not protocol or protocol.upper() not in ["TCP", "UDP"]:
            output("Please provide a valid protocol\n")
            return
        
        steps = send_packet(self.mn, self, {"protocol": protocol})
        
        output("\n***\n"+" -> ".join([step.get("name") for step in steps])+ "\n***\n")


    def default(self, line):
        """Fallback to the default CLI behavior for unrecognized commands."""
        return super().default(line)
    

def send_packet(mn: Mininet, cli: CustomCLI, packet_info: Dict) -> Dict:
    # TODO: use constants
    response = requests.post(f"http://{CONTROLLER_IP}:{CONTROLLER_PORT}{ApiPaths.RECORDINGS()}")
    
    recording_id = response.json()["recording_id"]

    protocol = packet_info.get("protocol")

    # run python script inside node h1
    h1 = mn.get("h1")
    h1.sendCmd(f"python3 commands/send_packet.py -ip 10.0.0.3 -t {protocol} -p 9999")
    # TODO: override output to avoid printing in the console
    cli.waitForNode(h1)

    time.sleep(1)

    # api request to retrieve packet recording
    return requests.get(f"http://{CONTROLLER_IP}:{CONTROLLER_PORT}{ApiPaths.RECORDING(recording_id)}").json()



def poll_apis_for_packets(args: Dict):
    """Poll the APIs for packets requests."""
    print("Polling APIs for packets requests...")
    mn = args["mn"]
    cli = args["cli"]
    while True and not stopping_flag.is_set():
        # Poll the API for packets requests
        time.sleep(1)
        response = requests.get(f"http://{CONTROLLER_IP}:{CONTROLLER_PORT}{ApiPaths.PACKET()}")
        # print("polling_result", response.status_code, response.json())
        if response.status_code == 200:
            packet_info = response.json()
            # Send packet to the network
            if packet_info.get("status") == "available":
                # Send the packet to the network
                packet_id = packet_info.get("packet_id")
                packet_result = send_packet(mn, cli, packet_info)
                print("packet_result", packet_result)
                # Save the packet result
                requests.post(f"http://{CONTROLLER_IP}:{CONTROLLER_PORT}{ApiPaths.PACKET_RESULT(packet_id)}", json=packet_result)
                
    print("Stopping polling thread...")


if __name__ == "__main__":
    topo = NetworkSlicingTopology()
    topo.start()
