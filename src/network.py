#!/usr/bin/python3

import time
from mininet.log import setLogLevel, output
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.cli import CLI
from mininet.link import TCLink

from common.constants import DEBUG
import logging

# Configure logging to remove duplicate logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('mininet')
logger.setLevel(logging.INFO)
logger.propagate = False  # Disable propagation to avoid duplicate logs


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
        # Using a custom CLI instead of the default one
        CustomCLI(net)
        net.stop()


class CustomCLI(CLI):
    """A custom CLI to add new commands."""
    first_cmd = True

    def preloop(self):
        """Executed before entering the CLI loop."""
        if self.first_cmd:
            self.wait_for_nodes()
            self.first_cmd = False

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
        Usage: slice <test_id>
        """
        test_id = line.strip()
        if not test_id or not test_id.isdigit():
            output("Please provide a valid test ID.\n")
            return
        output("Performing bandwidth test %s...\n" % test_id)
        # h3 iperf -s -u -p 9999 -b 10M -t 30 & (start listening on h3 as server in background for around 30s)
        # h1 iperf -c 10.0.0.3 -u -p 9999 -b 10M -t 10 -i 1 (start sending on h1 as a client, 10 times with interval 1s)
        server = self.mn.getNodeByName("h3")
        client = self.mn.getNodeByName("h1")
        # server.cmd("iperf -s -u -p 9999 -b 10M -t 30 &")
        # client.cmd("iperf -c 10.0.0.3 -u -p 9999 -b 10M -t 10 -i 1")
        result = self.mn.iperf((client, server), l4Type='UDP', udpBw='10M', seconds=10, port=9999)
        output(f"Bandwidth test result: {result}\n")

    def default(self, line):
        """Fallback to the default CLI behavior for unrecognized commands."""
        return super().default(line)


if __name__ == "__main__":
    topo = NetworkSlicingTopology()
    topo.start()
