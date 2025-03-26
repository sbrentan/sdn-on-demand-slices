from __future__ import annotations

import json
import uuid
import logging
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

    @property
    def rules_dict(self) -> dict:
        def serialize(obj):
            if isinstance(obj, Protocol):
                return obj.value
            raise TypeError(f"Type {type(obj)} not serializable")

        return json.loads(json.dumps(self.rules, default=serialize))

    @staticmethod
    def get_slice_id(slice: Optional[Slice] = None) -> str:
        if slice:
            return slice.id
        raise ValueError("No slice provided")

    def is_protocol_valid(self, pkt_protocol: Protocol) -> bool:
        if not self.active:
            return False
        if not self.rules["allowed_protocols"]:
            return True
        return pkt_protocol in self.rules["allowed_protocols"]

    def is_port_valid(self, pkt_protocol: Protocol, pkt: Packet) -> bool:
        if not self.active:
            return False
        if not self.rules["allowed_ports"]:
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
                logging.info("No UDP header found")
                return False
            port = udp_header.dst_port  # type: ignore
        else:
            return False
        logging.info(f"Checking port {port}")
        return port in self.rules["allowed_ports"]

    def __post_init__(self):
        if not self.name:
            self.name = self.id
        self._validate_rules()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "rules": self.rules_dict,
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
        self._validate_rules()

    @staticmethod
    def from_dict(data: dict) -> Slice:
        slice = Slice(
            id=data.get("id", uuid.uuid4().hex),
            rules=data.get("rules", {"allowed_protocols": None, "allowed_ports": None, "allowed_services": None}),
            switches=data.get("switches", []),
            hosts=data.get("hosts", []),
            active=str(data.get("active", "True")).upper() == "TRUE" if "active" in data else True,
            min_rate=data.get("min_rate", None),
            max_rate=data.get("max_rate", None)
        )
        if "name" in data:
            slice.name = data["name"]
        return slice
    
    def _validate_rules(self):
        if "allowed_protocols" not in self.rules:
            self.rules["allowed_protocols"] = None  # If none, no rule is enforced
        else:
            if not isinstance(self.rules["allowed_protocols"], list):
                raise ValueError("Invalid allowed protocols")
            for idx, p in enumerate(self.rules["allowed_protocols"]):
                if isinstance(p, Protocol):
                    if p not in Protocol.all():
                        raise ValueError(f"Invalid protocol {p}")
                elif isinstance(p, str):
                    if p not in [p.value for p in Protocol]:
                        raise ValueError(f"Invalid protocol {p}")
                    self.rules["allowed_protocols"][idx] = Protocol(p)
                else:
                    raise ValueError(f"Invalid protocol {p}")
        if "allowed_ports" not in self.rules:
            self.rules["allowed_ports"] = None  # If none, no rule is enforced
        else:
            if not isinstance(self.rules["allowed_ports"], list):
                raise ValueError("Invalid allowed ports")
            new_ports = []
            for port in self.rules["allowed_ports"]:
                new_port = port
                if isinstance(port, str):
                    try:
                        new_port = int(port)
                    except ValueError:
                        raise ValueError(f"Invalid port {port}")
                if not isinstance(new_port, int):
                    raise ValueError(f"Invalid port {port}")
                new_ports.append(new_port)
            self.rules["allowed_ports"] = new_ports

        if "allowed_services" not in self.rules:
            self.rules["allowed_services"] = None
        else:
            # check structure is valid: {host ip: [port]}
            if not isinstance(self.rules["allowed_services"], dict):
                raise ValueError("Invalid allowed services")
            for host_ip, ports in self.rules["allowed_services"].items():
                if not isinstance(host_ip, str):
                    raise ValueError(f"Invalid host IP {host_ip}")
                if not isinstance(ports, list):
                    raise ValueError(f"Invalid ports for host {host_ip}")
                new_ports = []
                for port in ports:
                    new_port = port
                    if isinstance(port, str):
                        try:
                            new_port = int(port)
                        except ValueError:
                            raise ValueError(f"Invalid port {port}")
                    if not isinstance(new_port, int):
                        raise ValueError(f"Invalid port {port}")
                    new_ports.append(new_port)
                self.rules["allowed_services"][host_ip] = new_ports
        
        if not any([self.rules[r] for r in self.rules]):
            raise ValueError("No rules specified")
    
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
