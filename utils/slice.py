from __future__ import annotations

import logging
from typing import Dict, List, Tuple, Optional
from enum import Enum
from dataclasses import dataclass

from ryu.lib.packet.packet import Packet
from ryu.lib.packet.packet_base import PacketBase
from ryu.lib.packet import ethernet, ipv4, icmp, tcp, udp, ether_types

from utils.topology import Connection

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

    name: str
    rules: dict
    switches: List[str]
    hosts: List[str]
    active: bool = True
    min_rate: Optional[int] = None  # In bps
    max_rate: Optional[int] = None  # In bps

    @staticmethod
    def get_slice_id(slice: Optional[Slice] = None) -> str:
        if slice:
            return slice.name
        raise ValueError("No slice provided")
        return "__no_slice"

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
        
    def is_services_valid(self, pkt: Packet) -> bool:
        services_valid = True
        if self.rules["allowed_services"] is not None:
            services_valid = False
            ip_header = pkt.get_protocol(ipv4.ipv4)
            if ip_header is None:
                return False
            src = ip_header.src #type: ignore
            dst = ip_header.dst #type: ignore
            pkt_protocol = Protocol.from_id(ip_header.proto)  # type: ignore
            l4_packet = SliceUtils.get_l4_packet(pkt, pkt_protocol)
            if l4_packet is None:
                return False
            src_port = l4_packet.src_port  # type: ignore
            dst_port = l4_packet.dst_port  # type: ignore
            if src in self.rules["allowed_services"]:
                if src_port in self.rules["allowed_services"][src]:
                    services_valid = True
            if dst in self.rules["allowed_services"]:
                if dst_port in self.rules["allowed_services"][dst]:
                    services_valid = True
        return services_valid

    def __post_init__(self):
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
        
        # if self.name != Slice.get_slice_id():
        if not any([self.rules[r] for r in self.rules]):
            raise ValueError("No rules specified")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "rules": self.rules,
            "nodes": self.switches + self.hosts,
            "active": self.active,
            "min_rate": self.min_rate,
            "max_rate": self.max_rate
        }
    
    def update_from_dict(self, data: dict):
        # TODO: is slice.name the actual slice id? or should slice_id be introduced?
        self.rules = data["rules"] if "rules" in data else self.rules
        self.switches = [n for n in data["nodes"] if n.startswith("s")] if "nodes" in data else self.switches # TODO: change
        self.hosts = [n for n in data["nodes"] if n.startswith("h")] if "nodes" in data else self.hosts # TODO: change
        self.active = bool(data["active"]) if "active" in data else self.active,
        self.min_rate = data["min_rate"] if "min_rate" in data else self.min_rate
        self.max_rate = data["max_rate"] if "max_rate" in data else self.max_rate 
        # TODO: call self.__post_init__() to validate rules??    

    def activate(self):
        logging.info(f"Activating slice {self.name}")
        self.active = True
    
    def deactivate(self):
        logging.info(f"Deactivating slice {self.name}")
        self.active = False

    @staticmethod
    def from_dict(data: dict) -> Slice:
        return Slice(
            name=data["name"],
            rules=data["rules"],
            switches=[n for n in data["nodes"] if n.startswith("s")], # TODO: change
            hosts=[n for n in data["nodes"] if n.startswith("h")], # TODO: change
            active=bool(data["active"]) if "active" in data else False,
            min_rate=data.get("min_rate"),
            max_rate=data.get("max_rate")
        )
    
    def __repr__(self) -> str:
        return f"Slice({self.name}) - Switches: {self.switches} - Hosts: {self.hosts}"
    
    def __str__(self) -> str:
        return self.__repr__()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Slice):
            return NotImplemented
        return self.name == other.name

    def __in__(self, other: object) -> bool:
        if not isinstance(other, List):
            return NotImplemented
        for s in other:
            if not isinstance(s, Slice):
                return NotImplemented
            if self == s:
                return True
        return False


class SliceUtils:

    link_to_slice_dict: Dict[str, List[Slice]]
    node_connections: Dict[str, List[Connection]]
    
    def __init__(self, link_to_slice_dict: dict, node_connections: dict):
        self.link_to_slice_dict = link_to_slice_dict
        self.node_connections = node_connections

    def get_in_connection(self, switch_id: str, in_port: int) -> Optional[Connection]:
        """
        Get the incoming connection of the packet

        Args:
            switch_id (str): ID of the switch where the packet came from (e.g. s1)
            in_port (int): Port number where the packet came from
        
        Returns:
            Connection: Incoming connection of the packet
        """
        connections = self.node_connections.get(switch_id, [])
        logging.info(f"[get_in_connection] Switch connections: {connections} for switch {switch_id}")
        for connection in connections:
            src_valid = connection.src[1].node_id == switch_id and connection.src[0].port_no == in_port
            dst_valid = connection.dst[1].node_id == switch_id and connection.dst[0].port_no == in_port
            logging.info(f"[get_in_connection] Checking connection: {connection.src[1].node_id} - {connection.dst[1].node_id} - {connection.src[0].port_no} - {connection.dst[0].port_no} - {in_port} - {switch_id}")
            if src_valid or dst_valid:
                logging.info(f"[get_in_connection] IN Connection: {connection}")
                return connection
        return None

    def is_slice_valid_for_pkt(self, slice: Slice, pkt_protocol: Protocol, pkt: Packet) -> bool:
        """
        Validate if the packet belongs to the slice

        Args:
            slice (Slice): Slice object
            pkt_protocol (Protocol): Protocol of the packet
            pkt (Packet): Packet object
        
        Returns:
            bool: True if the packet belongs to the slice, False otherwise
        """
        logging.info(f"[is_slice_valid_for_pkt] Slice: {slice}")
        if slice.is_protocol_valid(pkt_protocol):
            logging.info("[is_slice_valid_for_pkt] Protocol valid")
        else:
            return False

        if slice.is_port_valid(pkt_protocol, pkt):
            logging.info("[is_slice_valid_for_pkt] Port valid")
        else:
            return False

        if slice.is_services_valid(pkt):
            logging.info("[is_slice_valid_for_pkt] Services valid")
        else:
            return False
                
        return True
        
    def get_slices_from_packet(self, switch_id: str, pkt: Packet, in_connection: Connection) -> List[Slice]:
        """
        Get the slices that the packet belongs to
        If the packet is from a host, the packet is not part of any slice and therefore the slices are retrieved based on the incoming packet

        Args:
            switch_id (str): ID of the switch where the packet came from (e.g. s1)
            pkt (Packet): Packet object
        
        Returns:
            List[Slice]: List of slices that the packet belongs to
        """
        logging.info(f"[get_slice_from_packet] Packet: {pkt}")
        try:
            pkt_protocol = self.get_packet_protocol(pkt)
        except ValueError:
            return []

        result = []
        
        slices = self.link_to_slice_dict.get(in_connection.link_id, [])
        logging.info(f"[get_slice_from_packet] Slices: {slices}")
        for slice in slices:
            if (self.is_slice_valid_for_pkt(slice, pkt_protocol, pkt)):
                logging.info(f"[get_slice_from_packet] Slice found: {slice}")
                result.append(slice)
        if not result:
            logging.info("[get_slice_from_packet] No slice found")
        return result

    @staticmethod
    def get_l3_packet(pkt: Packet) -> Optional[PacketBase]:
        eth_header = pkt.get_protocol(ethernet.ethernet)
        src = eth_header.src # type: ignore
        dst = eth_header.dst # type: ignore

        logging.info(f"[_get_protocol_from_packet] L2 src: {src}, dst: {dst}")
        
        if eth_header.ethertype == ether_types.ETH_TYPE_LLDP: # type: ignore
            return None
        
        ipv4_header = pkt.get_protocol(ipv4.ipv4)
        if ipv4_header is None:
            logging.info("[_get_protocol_from_packet] No IP header found")
            return None
        
        return pkt.get_protocol(ipv4.ipv4)

    @staticmethod
    def get_l4_packet(pkt: Packet, pkt_protocol: Optional[Protocol]) -> Optional[PacketBase]:
        if pkt_protocol is None:
            return None
        if pkt_protocol == Protocol.TCP:
            return pkt.get_protocol(tcp.tcp)
        elif pkt_protocol == Protocol.UDP:
            return pkt.get_protocol(udp.udp)
        elif pkt_protocol == Protocol.ICMP:
            return pkt.get_protocol(icmp.icmp)
        else:
            return None

    def get_packet_protocol(self, pkt: Packet) -> Protocol:
        l3_packet = self.get_l3_packet(pkt)
        if l3_packet is None:
            raise ValueError("No L3 packet found")
        return Protocol.from_id(l3_packet.proto)  # type: ignore
