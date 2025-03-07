from dataclasses import dataclass
from typing import Optional

from ryu.topology.switches import Switch

from .network import Connection
from .slice import Slice
from .constants import NETWORK_MAX_RATE

@dataclass
class Queue:

    switch: Switch
    connection: Connection
    queue_id: int
    min_rate: Optional[int] = None
    max_rate: Optional[int] = None
    slice: Optional[Slice] = None

    def __post_init__(self):
        if not self.max_rate:
            self.max_rate = NETWORK_MAX_RATE

    def determine_out_port(self, dpid: int) -> int:
        out_port = self.connection.src[0].port_no if self.connection.src[0].dpid == dpid else self.connection.dst[0].port_no
        return out_port
    
    def to_queue_dict(self):
        # TODO: change this if OVSBridge is used instead of REST API
        queue_dict = {}
        if self.min_rate is not None:
            queue_dict["min_rate"] = str(self.min_rate)
        if self.max_rate is not None:
            queue_dict["max_rate"] = str(self.max_rate)
        return queue_dict
