import time
import requests
import threading
from typing import Dict

from mininet.cli import CLI
from mininet.net import Mininet
from mininet.log import output, setLogLevel
from common.constants import CONTROLLER_IP, CONTROLLER_PORT
from common.paths import ApiPaths
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
        
        steps = make_host_send_packet(self.mn, self, {"protocol": protocol})
        
        output("\n***\n"+" -> ".join([step.get("name") for step in steps])+ "\n***\n")


    def default(self, line):
        """Fallback to the default CLI behavior for unrecognized commands."""
        return super().default(line)



def make_host_send_packet(mn: Mininet, cli: CustomCLI, packet_info: Dict) -> Dict:
    response = requests.post(f"http://{CONTROLLER_IP}:{CONTROLLER_PORT}{ApiPaths.RECORDINGS()}")
    
    recording_id = response.json()["recording_id"]

    protocol = packet_info.get("protocol")

    # run python script inside node h1
    h1 = mn.get("h1")
    h1.sendCmd(f"python3 cli/send_packet.py -ip 10.0.0.3 -t {protocol} -p 9999")
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
                packet_result = make_host_send_packet(mn, cli, packet_info)
                # Save the packet result
                requests.post(f"http://{CONTROLLER_IP}:{CONTROLLER_PORT}{ApiPaths.PACKET_RESULT(packet_id)}", json=packet_result)
    print("Stopping polling thread...")
