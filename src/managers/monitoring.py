from typing import Any, Dict, List, Tuple
from common import Node
from ryu.lib.packet.packet import Packet

class MonitoringManager:

    recordings: Dict[int, List[Tuple[Node, Packet]]] = {}
    recordings_last_id: int = 0

    @property
    def active_recording(self) -> bool:
        return self.recordings_last_id in self.recordings

    def new_recording(self) -> int:
        self.recordings_last_id += 1
        self.recordings[self.recordings_last_id] = []
        return self.recordings_last_id
        
    def add_recording_step(self, node: Node, packet: Packet):
        if not self.active_recording:
            raise ValueError("No active recording")
        self.recordings[self.recordings_last_id].append((node, packet))

    def get_recording(self, recording_id: int) -> List[Tuple[Node, Packet]]:
        if recording_id not in self.recordings:
            raise ValueError("Invalid recording ID")
        result = self.recordings[self.recordings_last_id]
        del self.recordings[self.recordings_last_id]
        return result
