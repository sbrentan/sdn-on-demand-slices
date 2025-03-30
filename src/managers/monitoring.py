import logging
from typing import Dict, List, Tuple, Optional

from common import Node, NodeType, PacketInfo, Connection
from ryu.lib.packet.packet import Packet


class MonitoringManager:

    packets: Dict[int, List[Dict]] = {}
    packets_last_id: int = 0
    packets_result: Dict[int, Dict] = {}

    recordings: Dict = {}
    recordings_last_id: int = 0

    @property
    def active_recording(self) -> bool:
        return self.recordings_last_id in self.recordings
    
    @property
    def active_packet(self) -> bool:
        return self.packets_last_id in self.packets
    
    def send_packet(self, packet_info: PacketInfo) -> int:
        self.packets_last_id += 1
        self.packets[self.packets_last_id] = packet_info
        return self.packets_last_id
    
    def get_packet(self, packet_id: Optional[int] = None) -> PacketInfo:
        if not packet_id:
            packet_id = list(self.packets.keys())[0]
        if packet_id not in self.packets:
            raise ValueError("Invalid packet ID")
        result = self.packets[self.packets_last_id]
        result["packet_id"] = packet_id
        del self.packets[self.packets_last_id]
        return result
    
    def save_packet_result(self, packet_id: int, result: Dict):
        logging.info(f"Saving packet result for packet {packet_id}: {result}")
        self.packets_result[packet_id] = result

    def get_packet_result(self, packet_id: int) -> Dict:
        if packet_id not in self.packets_result:
            raise ValueError("Invalid packet ID")
        result = self.packets_result[packet_id]
        del self.packets_result[packet_id]
        return result
    
    def packet_result_is_available(self, packet_id: int) -> bool:
        logging.info(f"Checking if packet result is available for packet {packet_id}: {self.packets_result}")
        return packet_id in self.packets_result

    def new_recording(self) -> int:
        self.recordings_last_id += 1
        self.recordings[self.recordings_last_id] = []
        return self.recordings_last_id

    def add_recording_step(self, node: Node, in_connection: Connection):
        logging.info(f"Adding recording step for node {node.node_id} with connection {in_connection}")
        if not self.active_recording:
            raise ValueError("No active recording")
        if not self.recordings[self.recordings_last_id]:
            if not in_connection.is_host_connection:
                raise ValueError("First recording step must be a host connection")
            self.recordings[self.recordings_last_id] = {
                "id": in_connection.host_mac,
                "children": [{
                    "id": node.node_id,
                    "children": []
                }]
            }
        else:
            previous_node = in_connection.src[1] if node.node_id == in_connection.dst[1].node_id else in_connection.dst[1]
            logging.info(f"Previous node: {previous_node.node_id}")
            # Look for previous node id in recording using a queue
            def find_and_update_path(node, target_id, path):
                path.append(node["id"])
                found = False
                for child in node["children"]:
                    if find_and_update_path(child, target_id, path):
                        found = True
                if node["id"] == target_id:
                    found = True
                if not found:
                    path.pop()
                return found

            path = []
            logging.info(f"Finding path to node {previous_node.node_id} in recording {self.recordings[self.recordings_last_id]}")
            if not find_and_update_path(self.recordings[self.recordings_last_id], previous_node.node_id, path):
                raise ValueError("Previous node not found in the recording")

            # Traverse the path to update the recording
            current = self.recordings[self.recordings_last_id]
            for node_id in path[1:]:
                for child in current["children"]:
                    if child["id"] == node_id:
                        current = child
                        break

            if node.node_id in [c["id"] for c in current["children"]]:
                logging.info("Skipping recording step because it is duplicated")
                return

            # Add the new node to the children of the last node in the path
            current["children"].append({
                "id": node.node_id,
                "children": []
            })


    def get_recording(self, recording_id: int) -> List[Tuple[Node, Packet]]:
        if recording_id not in self.recordings:
            raise ValueError("Invalid recording ID")
        result = self.recordings[self.recordings_last_id]
        del self.recordings[self.recordings_last_id]
        return result
