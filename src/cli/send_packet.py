import socket
import argparse
import subprocess
import re
import struct
import os
import time

DSCP_TAG_VALUE = 32

# TODO: manage ICMP packet

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

def checksum(source_string):
    """Compute the Internet Checksum of the supplied data."""
    sum = 0
    max_count = (len(source_string) // 2) * 2
    count = 0
    while count < max_count:
        # ord() is not needed for bytes in Python 3.
        val = source_string[count + 1] * 256 + source_string[count]
        sum = sum + val
        sum = sum & 0xffffffff  # Necessary?
        count += 2

    if max_count < len(source_string):
        sum += source_string[-1]
        sum = sum & 0xffffffff

    sum = (sum >> 16) + (sum & 0xffff)
    sum = sum + (sum >> 16)
    answer = ~sum & 0xffff
    # Swap bytes.
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer

def create_icmp_packet(id, sequence, payload=b'ICMP packet'):
    """Create a raw ICMP Echo Request packet."""
    icmp_type = 8  # Echo Request
    icmp_code = 0
    checksum_val = 0  # initial checksum is zero
    header = struct.pack("!BBHHH", icmp_type, icmp_code, checksum_val, id, sequence)
    # Calculate checksum on header + payload
    checksum_val = checksum(header + payload)
    header = struct.pack("!BBHHH", icmp_type, icmp_code, checksum_val, id, sequence)
    return header + payload

print("Host MAC address:", get_mac_address())

# Get the host's IP using ifconfig
host_ip = get_host_ip_from_ifconfig()

# Parse command-line arguments
protocol_choices = ["UDP", "TCP", "ICMP"]
temp = []
for p in protocol_choices:
    temp.append(p.lower())
protocol_choices += temp
parser = argparse.ArgumentParser(description="Send a single packet via UDP or TCP.")
parser.add_argument("-ip", required=True, help="Destination IP address")
parser.add_argument("-p", type=int, required=True, help="Destination port")
parser.add_argument("-sp", type=int, help="Source port (optional)")
parser.add_argument("-t", choices=protocol_choices, required=True, help="Protocol type (UDP or TCP)")
args = parser.parse_args()

# Configuration from arguments
destination_ip = args.ip
destination_port = args.p
source_port = args.sp
protocol = args.t.upper()

sock = None

try:
    print(f"Sending a single {protocol} packet from {host_ip}:{source_port} to {destination_ip}:{destination_port}")
    if protocol == "UDP":

        # Create a UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", source_port if source_port else 0))

        dscp_value = DSCP_TAG_VALUE
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, dscp_value)

        # Send a single packet
        sock.sendto(b"UDP message", (destination_ip, destination_port))
    elif protocol == "TCP":

        # Create a TCP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("0.0.0.0", source_port if source_port else 0))
        
        dscp_value = DSCP_TAG_VALUE
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, dscp_value)

        # Connect to the server
        try:
            sock.connect((destination_ip, destination_port))

            # Send a single packet
            sock.sendall(b"TCP message")
        except ConnectionRefusedError:
            print("- Connection refused by the server")
    elif protocol == "ICMP":
        # Raw socket creation requires root privileges.
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        # Optional: set DSCP on the IP layer
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, DSCP_TAG_VALUE)
        
        # Create an ICMP echo request packet.
        packet_id = os.getpid() & 0xFFFF  # Use PID as packet ID
        packet_sequence = 1
        icmp_packet = create_icmp_packet(packet_id, packet_sequence)
        
        # Send the packet. Note: the second parameter's port is not used by ICMP.
        sock.sendto(icmp_packet, (destination_ip, 0))
        print("ICMP packet sent.")
        
        # Optionally, you might want to wait for a reply:
        sock.settimeout(2)
        try:
            reply, addr = sock.recvfrom(1024)
            print("Received reply from", addr)
        except socket.timeout:
            print("Request timed out.")
        
    else:
        print("Unsupported protocol.")
except Exception as e:
    import traceback
    print("Error:", e)
    traceback.print_exc()
finally:
    # Close the socket
    if sock:
        sock.close()
