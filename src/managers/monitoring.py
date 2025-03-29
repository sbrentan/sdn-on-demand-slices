import logging
from typing import Dict, List, Tuple, Optional

from common import Node, NodeType, PacketInfo
from ryu.lib.packet.packet import Packet


class MonitoringManager:

    packets: Dict[int, List[Dict]] = {}
    packets_last_id: int = 0
    packets_result: Dict[int, Dict] = {}

    recordings: Dict[int, List[Tuple[Node, Packet]]] = {}
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
        
    def add_recording_step(self, node: Node, packet: Packet):
        if not self.active_recording:
            raise ValueError("No active recording")
        if self.recordings[self.recordings_last_id]:
            last_node = self.recordings[self.recordings_last_id][-1][0]
            if last_node.node_type == NodeType.HOST:
                if last_node.node_id == node.node_id:
                    logging.info("Skipping recording step because it is the same host")
                    return
        self.recordings[self.recordings_last_id].append((node, packet))

    def get_recording(self, recording_id: int) -> List[Tuple[Node, Packet]]:
        if recording_id not in self.recordings:
            raise ValueError("Invalid recording ID")
        result = self.recordings[self.recordings_last_id]
        del self.recordings[self.recordings_last_id]
        return result
