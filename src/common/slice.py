from __future__ import annotations

import json
import uuid
from typing import List, Optional
from enum import Enum
from dataclasses import dataclass

from ryu.lib.packet.packet import Packet
from ryu.lib.packet import tcp, udp

class Protocol(Enum):
    TCP = "TCP"
    UDP = "UDP"
    ICMP = "ICMP"

    @staticmethod
    def all():
        return [p.value for p in Protocol]
    
    @property
    def protocol_id(self) -> int:
        if self == Protocol.TCP:
            return 0x6
        elif self == Protocol.UDP:
            return 0x11
        elif self == Protocol.ICMP:
            return 0x1
        else:
            raise ValueError("Invalid protocol")

    @staticmethod
    def from_id(protocol_id: int) -> Protocol:
        for p in Protocol:
            if p.protocol_id == protocol_id:
                return p
        raise ValueError("Invalid protocol id")
        
    def __str__(self):
        return self.value
    
    def __repr__(self):
        return f'"{self.value}"'


@dataclass
class Slice:

    id: str
    rules: dict
    switches: List[str]
    hosts: List[str]
    active: bool = True
    min_rate: Optional[int] = None  # In bps
    max_rate: Optional[int] = None  # In bps

    name: Optional[str] = None

    @staticmethod
    def get_slice_id(slice: Optional[Slice] = None) -> str:
        if slice:
            return slice.id
        raise ValueError("No slice provided")

    def is_protocol_valid(self, pkt_protocol: Protocol) -> bool:
        if not self.active:
            return False
        if self.rules["allowed_protocols"] is None:
            return True
        return pkt_protocol in self.rules["allowed_protocols"]

    def is_port_valid(self, pkt_protocol: Protocol, pkt: Packet) -> bool:
        if not self.active:
            return False
        if self.rules["allowed_ports"] is None:
            return True
        if pkt_protocol == Protocol.ICMP:
            return True
        if pkt_protocol == Protocol.TCP:
            tcp_header = pkt.get_protocol(tcp.tcp)
            if tcp_header is None:
                return False
            port = tcp_header.dst_port  # type: ignore
        elif pkt_protocol == Protocol.UDP:
            udp_header = pkt.get_protocol(udp.udp)
            if udp_header is None:
                return False
            port = udp_header.dst_port  # type: ignore
        else:
            return False
        return port in self.rules["allowed_ports"]

    def __post_init__(self):
        if not self.name:
            self.name = self.id
        # Validate rules
        if "allowed_protocols" not in self.rules:
            self.rules["allowed_protocols"] = None  # If none, no rule is enforced
        else:
            if not isinstance(self.rules["allowed_protocols"], list):
                raise ValueError("Invalid allowed protocols")
            for idx, p in enumerate(self.rules["allowed_protocols"]):
                if p not in Protocol.all():
                    raise ValueError(f"Invalid protocol {p}")
                self.rules["allowed_protocols"][idx] = Protocol(p)
        if "allowed_ports" not in self.rules:
            self.rules["allowed_ports"] = None  # If none, no rule is enforced

        if "allowed_services" not in self.rules:
            self.rules["allowed_services"] = None
        else:
            # check structure is valid: {host ip: [port]}
            if not isinstance(self.rules["allowed_services"], dict):
                raise ValueError("Invalid allowed services")
            for host_ip, ports in self.rules["allowed_services"].items():
                if not isinstance(host_ip, str):
                    raise ValueError("Invalid host IP")
                if not isinstance(ports, list):
                    raise ValueError("Invalid ports")
                for port in ports:
                    if not isinstance(port, int):
                        raise ValueError("Invalid port")
        
        if not any([self.rules[r] for r in self.rules]):
            raise ValueError("No rules specified")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "rules": self.rules,
            "nodes": self.switches + self.hosts,
            "active": self.active,
            "min_rate": self.min_rate,
            "max_rate": self.max_rate
        }
    
    def update_from_dict(self, data: dict):
        if isinstance(data, str):
            data = json.loads(data)
        self.name = data["name"] if "name" in data else self.name
        self.rules = data["rules"] if "rules" in data else self.rules
        # TODO: implement hosts and switcheds update from data
        # self.switches = data["switches"] if "nodes" in data else self.switches # TODO: change
        # self.hosts = data['hosts'] if "nodes" in data else self.hosts # TODO: change
        self.active = bool(data["active"]) if "active" in data else self.active
        self.min_rate = data["min_rate"] if "min_rate" in data else self.min_rate
        self.max_rate = data["max_rate"] if "max_rate" in data else self.max_rate
        # TODO: call self.__post_init__() to validate rules??

    @staticmethod
    def from_dict(data: dict) -> Slice:
        slice = Slice(
            id=uuid.uuid4().hex,
            rules=data["rules"],
            switches=data["switches"],
            hosts=data["hosts"],
            active=bool(data["active"]) if "active" in data else False,
            min_rate=data.get("min_rate", None),
            max_rate=data.get("max_rate", None)
        )
        if "name" in data:
            slice.name = data["name"]
        return slice
    
    def __repr__(self) -> str:
        return f"Slice({self.id}) - Switches: {self.switches} - Hosts: {self.hosts}"
    
    def __str__(self) -> str:
        return self.__repr__()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Slice):
            return NotImplemented
        return self.id == other.id

    def __in__(self, other: object) -> bool:
        if not isinstance(other, List):
            return NotImplemented
        for s in other:
            if not isinstance(s, Slice):
                return NotImplemented
            if self == s:
                return True
        return False
