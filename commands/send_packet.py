import socket
import argparse
import subprocess
import re

def get_host_ip_from_ifconfig():
    """Get the IP address of the host using the ifconfig command."""
    try:
        # Execute ifconfig and capture its output
        ifconfig_output = subprocess.check_output("ifconfig", shell=True).decode()
        
        # Look for an IPv4 address pattern (on eth0 or similar)
        match = re.search(r"eth0.*?inet (\d+\.\d+\.\d+\.\d+)", ifconfig_output, re.S)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Error determining IP from ifconfig: {e}")
    return "127.0.0.1"  # Fallback to localhost if unable to determine IP

def get_mac_address():
    """Retrieve the MAC address of the primary network interface."""
    try:
        # Execute ifconfig and capture its output
        ifconfig_output = subprocess.check_output("ifconfig", shell=True).decode()

        # Look for the MAC address pattern
        match = re.search(r"eth0.*?ether ([\w:]+)", ifconfig_output, re.S)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Error determining MAC address from ifconfig: {e}")
    return "00:00:00:00:00:00"  # Fallback MAC address

print("Host MAC address:", get_mac_address())

# Get the host's IP using ifconfig
host_ip = get_host_ip_from_ifconfig()

# Parse command-line arguments
protocol_choices = ["UDP", "TCP"]
temp = []
for p in protocol_choices:
    temp.append(p.lower())
protocol_choices += temp
parser = argparse.ArgumentParser(description="Send a single packet via UDP or TCP.")
parser.add_argument("-ip", required=True, help="Destination IP address")
parser.add_argument("-p", type=int, required=True, help="Destination port")
parser.add_argument("-t", choices=protocol_choices, required=True, help="Protocol type (UDP or TCP)")
args = parser.parse_args()

# Configuration from arguments
destination_ip = args.ip
destination_port = args.p
protocol = args.t.upper()

sock = None

try:
    print(f"Sending a single {protocol} packet from {host_ip} to {destination_ip}:{destination_port}")
    if protocol == "UDP":

        # Create a UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Send a single packet
        sock.sendto(b"UDP message", (destination_ip, destination_port))
    elif protocol == "TCP":

        # Create a TCP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Connect to the server
        sock.connect((destination_ip, destination_port))

        # Send a single packet
        sock.sendall(b"TCP message")
except Exception as e:
    print(f"Error: {e}")
finally:
    # Close the socket
    if sock:
        sock.close()
