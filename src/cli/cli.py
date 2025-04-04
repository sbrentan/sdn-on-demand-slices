import time
import argparse
import requests
import threading
from typing import Dict

from mininet.cli import CLI
from mininet.net import Mininet
from mininet.log import output, setLogLevel
from common.constants import CONTROLLER_IP, CONTROLLER_PORT
from common import ApiPaths, PacketInfo
from cli.bandwidth_tests import BandwidthTest

stopping_flag = threading.Event()


class CustomCLI(CLI):

    """A custom CLI to add new commands."""
    first_cmd = True
    polling_thread = None

    def preloop(self):
        """Executed before entering the CLI loop."""
        if self.first_cmd:
            self.first_cmd = False
            self.wait_for_nodes()

            # Start thread polling apis for packets requests
            self.polling_thread = threading.Thread(target=poll_apis_for_packets, args=({"mn": self.mn, "cli": self},))
            self.polling_thread.start()

    def postloop(self):
        if self.polling_thread and self.polling_thread.is_alive():
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

    def help_bwtest(self):
        """Display help for the bwtest command."""
        output("Custom command to perform bandwidth tests.\n")
        output("Usage: bwtest [-h] [-p PROTOCOL] [-port DST_PORT] [-src SRC] [-dst DST]\n")

    def do_bwtest(self, line):
        """
        Custom command to perform bandwidth tests.
        Usage: bwtest <test_id>
        """
        parser = argparse.ArgumentParser(description="Trace a packet through the network.")
        # parser.add_argument('-test_id', type=str, help="Test ID of the bandwidth test.")
        parser.add_argument("-p", "--protocol", type=str, help="Protocol of the bandwidth test (TCP or UDP).")
        parser.add_argument("-port", "--dst_port", type=int, help="Destination port of the packet.")
        parser.add_argument("-src", "--src", type=str, help="Source node of the packet.")
        parser.add_argument("-dst", "--dst", type=str, help="Destination node of the packet.")
        args, argv = parser.parse_known_args(line.split())
        if argv:
            output('unrecognized arguments: %s\n' % ' '.join(argv))
            return
        # valid_test_ids = BandwidthTest.get_test_ids()
        # if not args.test_id:
        protocol, dst_port, src, dst = args.protocol, args.dst_port, args.src, args.dst
        if not all([protocol, dst_port, src, dst]):
            output("Please provide all arguments for the bandwidth test (protocol, port, src, dst).\n")
            return
        if protocol not in ["TCP", "UDP"]:
            output("Please provide a valid protocol (TCP or UDP).\n")
            return
        if not isinstance(dst_port, int):
            output("Please provide a valid destination port.\n")
            return
        if not self.mn.getNodeByName(src) or not self.mn.getNodeByName(dst):
            output("Please provide valid source and destination nodes.\n")
            return
        src_mac = self.mn.getNodeByName(src).MAC()
        dst_mac = self.mn.getNodeByName(dst).MAC()
        packet_info = PacketInfo(
            protocol=protocol,
            dst_port=dst_port,
            src_mac=src_mac,
            dst_mac=dst_mac,
        )
        output("Performing bandwidth test...\n")
        BandwidthTest.run_test(test_id=None, mn=self.mn, packet_info=packet_info)
        # return
        # elif not args.test_id.isdigit():
        #     output(f"Please provide a valid test ID from {valid_test_ids}\n")
        #     return
        # output("Performing bandwidth test %s...\n" % args.test_id)
        # BandwidthTest.run_test(args.test_id, self.mn, line=line)
        # return

    def do_reset(self, line):
        """Custom command to reset the network flows and queues."""
        output("Resetting network flows and queues...\n")
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
        parser = argparse.ArgumentParser(description="Trace a packet through the network.")
        parser.add_argument("-p", "--protocol", type=str, required=True, help="Protocol of the packet (e.g., TCP, UDP, ICMP).")
        parser.add_argument("-port", "--dst_port", type=int, help="Destination port of the packet.")
        parser.add_argument("-src", "--src", type=str, required=True, help="Source node of the packet.")
        parser.add_argument("-dst", "--dst", type=str, required=True, help="Destination node of the packet.")

        try:
            args = parser.parse_args(line.split())
        except SystemExit:
            output("Invalid arguments for trace command.\n")
            return
        dst_port = 0
        if args.protocol in ["UDP", "TCP"]:
            if not args.dst_port:
                output("Please provide a destination port for UDP or TCP packets.\n")
                return
            dst_port = args.dst_port
        if args.dst_port and not isinstance(args.dst_port, int):
            output("Please provide a valid destination port.\n")
            return
        if args.src and args.dst:
            src_mac = self.mn.getNodeByName(args.src).MAC()
            dst_mac = self.mn.getNodeByName(args.dst).MAC()

        packet_info = PacketInfo(
            protocol=args.protocol,
            dst_port=dst_port,
            src_mac=src_mac,
            dst_mac=dst_mac,
        )
        steps = make_host_send_packet(self.mn, self, packet_info)
        
        # output("\n***\n"+" -> ".join([step.get("name") for step in steps])+ "\n***\n")
        print_packet_trace(steps)


    def default(self, line):
        """Fallback to the default CLI behavior for unrecognized commands."""
        return super().default(line)


def make_host_send_packet(mn: Mininet, cli: CustomCLI, packet_info: PacketInfo) -> Dict:
    response = requests.post(f"http://{CONTROLLER_IP}:{CONTROLLER_PORT}{ApiPaths.RECORDINGS()}")

    # output(f"Recording response: {response.status_code} {response.text}\n")
    
    recording_id = response.json()["recording_id"]

    protocol = packet_info.get("protocol")

    port = packet_info.get("dst_port")

    source_host = [h for h in mn.hosts if h.MAC() == packet_info.get("src_mac")][0]
    dst_ip = [h.IP() for h in mn.hosts if h.MAC() == packet_info.get("dst_mac")][0]

    output(f"Sending packet from {source_host.name} to {dst_ip} with protocol {protocol} and port {port}\n")

    # run python script inside node h1
    sp_str = f"-sp {packet_info.get('src_port')}" if packet_info.get("src_port") else ""
    source_host.sendCmd(f"python3 cli/send_packet.py -ip {dst_ip} -t {protocol} -p {port} {sp_str}")
    cli.waitForNode(source_host)

    time.sleep(1)

    # api request to retrieve packet recording
    response = requests.get(f"http://{CONTROLLER_IP}:{CONTROLLER_PORT}{ApiPaths.RECORDING(recording_id)}")
    if response.status_code == 200 and response.text:
        return response.json()
    else:
        output("Error retrieving packet recording\n")
        return {"steps": []}


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
                output(f"Received packet request: {packet_info}\n")
                packet_result = make_host_send_packet(mn, cli, packet_info)
                # Save the packet result
                requests.post(f"http://{CONTROLLER_IP}:{CONTROLLER_PORT}{ApiPaths.PACKET_RESULT(packet_id)}", json=packet_result)
    print("Stopping polling thread...")


def print_packet_trace(node, prefix="", is_last=True):
    """
    Recursively prints the packet flow in a structured way.
    
    :param node: A dict with an 'id' and an optional list of 'children'.
    :param prefix: String used for indentation.
    :param is_last: Boolean flag indicating if this node is the last among siblings.
    """
    # Choose a branch symbol: if this is the root, no symbol is needed.
    branch = ""
    if prefix:
        branch = "└─" if is_last else "├─"
    
    # Print current node with branch symbol.
    print(f"{prefix}{branch} → {node['id']}")
    
    # If there are no children, mark the end of this branch.
    children = node.get("children", [])
    if not children:
        print(f"{prefix}{'   ' if is_last else '│  '} 🔴 Packet ends at {node['id']}")
        return

    # Prepare a new prefix for children.
    new_prefix = prefix + ("   " if is_last else "│  ")
    
    # Recursively print each child.
    for index, child in enumerate(children):
        is_last_child = (index == len(children) - 1)
        print_packet_trace(child, new_prefix, is_last_child)
