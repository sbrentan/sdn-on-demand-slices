from __future__ import annotations

import logging
from typing import Dict, List, Tuple, Optional
from enum import Enum
from dataclasses import dataclass

from utils.topology import Connection, NodeType

from ryu.lib.packet.packet import Packet
from ryu.lib.packet.packet_base import PacketBase
from ryu.lib.packet import packet, ethernet, ipv4, ipv6, icmp, tcp, udp, ether_types


class Protocol(Enum):
    TCP = "tcp"
    UDP = "udp"
    ICMP = "icmp"

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


@dataclass
class Slice:

    name: str
    rules: dict
    switches: List[str]
    active: bool = True
    bandwidth: Optional[float] = None

    @staticmethod
    def get_slice_id(slice: Optional[Slice] = None) -> str:
        if slice:
            return slice.name
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
        

    def __post_init__(self):
        # Validate rules
        if "allowed_protocols" not in self.rules:
            self.rules["allowed_protocols"] = None  # If none, no rule is enforced
        else:
            for idx, p in enumerate(self.rules["allowed_protocols"]):
                if p not in Protocol.all():
                    raise ValueError(f"Invalid protocol {p}")
                self.rules["allowed_protocols"][idx] = Protocol(p)
        if "allowed_ports" not in self.rules:
            self.rules["allowed_ports"] = None  # If none, no rule is enforced
        
        if self.name != Slice.get_slice_id():
            if not any([self.rules[r] for r in self.rules]):
                raise ValueError("No rules specified")
    
    def __repr__(self) -> str:
        return f"Slice({self.name}) - Switches:{self.switches}"
    
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
    
    def __init__(self, link_to_slice_dict: dict, switch_connections: dict):
        self.link_to_slice_dict: Dict[str, List[Slice]] = link_to_slice_dict
        self.switch_connections: Dict[str, List[Connection]] = switch_connections

    def get_in_connection(self, switch_id: str, in_port: int) -> Optional[Connection]:
        """
        Get the incoming connection of the packet

        Args:
            switch_id (str): ID of the switch where the packet came from (e.g. s1)
            in_port (int): Port number where the packet came from
        
        Returns:
            Connection: Incoming connection of the packet
        """
        connections = self.switch_connections.get(switch_id, [])
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
            logging.info(f"[is_slice_valid_for_pkt] Protocol valid")
        else:
            return False

        if slice.is_port_valid(pkt_protocol, pkt):
            logging.info(f"[is_slice_valid_for_pkt] Port valid")
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
        
        if in_connection.is_host_connection:
            # If the incoming connection is from a host, the packet is not part of any slice
            # Detect the slices that the packet belongs to based on the incoming packet
            # result.append(Slice(name=Slice.get_slice_id(), rules={}, switches=[]))
            connections = self.switch_connections.get(switch_id, [])
            for connection in connections:
                if connection == in_connection:
                    continue
                connection_slices = self.link_to_slice_dict.get(connection.link_id, [])
                for slice in connection_slices:
                    if self.is_slice_valid_for_pkt(slice, self.get_packet_protocol(pkt), pkt) and slice not in result:
                        logging.info(f"[get_slices_from_packet] Slice detected for incoming host packet: {slice}")
                        result.append(slice)
        else:
            logging.info(f"[get_slice_from_packet] Connection: {in_connection}")
            slices = self.link_to_slice_dict.get(in_connection.link_id, [])
            for slice in slices:
                if (self.is_slice_valid_for_pkt(slice, pkt_protocol, pkt)):
                    logging.info(f"[get_slice_from_packet] Slice found: {slice}")
                    result.append(slice)
            if not result:
                # Assuming that host connections are slice independent and are never assigned to a slice
                logging.info("[ERROR] [get_slice_from_packet] No slice found")
        return result

    def get_links_for_slices(self, switch_id: str, slices: List[Slice], in_connection: Connection, pkt: Packet) -> Dict[str, Tuple[Connection, Optional[Slice], int]]:
        """
        Get the links that are part of the slices, excluding the in_connection
        If there are no slices, assuming the incoming packet is not part of any slice
        Assuming that if slices are not empty, all the outgoing connections that are not part of a slice are not allowed

        If the packet belongs to a slice:
        - If some outgoing connections are found for the slice, return those
        - For all the other cases, return empty Dict (meaning the packet should be dropped)
        If the packet does not belong to a slice:
        - Return all the outgoing connections which are not part of any slice

        Args:
            switch_id (str): ID of the switch where the packet came from (e.g. s1)
            slices (Dict[Slice]): Dict of slices that the packet belongs to
            in_connection (Connection): Incoming connection of the packet

        Returns:
            Dict[Tuple[Connection, int]]: Dict of outgoing connections and the queue id
        """
        connections = self.switch_connections.get(switch_id, [])
        eth_header = pkt.get_protocol(ethernet.ethernet)
        logging.info(f"[get_links_for_slices] Switch {switch_id} connections: {connections}")
        outgoing_connections = {}

        for connection in connections:
            if connection == in_connection:
                continue
            # If the connection is with the destinated host, just forward the packet
            # Assuming src is always the host in the connection
            if connection.src[1].node_type == NodeType.HOST and connection.src[1].node_ref.mac == eth_header.dst:  # type: ignore
                return {connection.link_id: (connection, None, 0)}
            link_id = connection.link_id
            logging.info(f"[get_links_for_slices] Connection: {link_id}")

            for slice in slices:
                try:
                    queue_id = self.link_to_slice_dict[link_id].index(slice) + 1
                    logging.info(f"[get_links_for_slices] Slice found: {slice} with queue_id: {queue_id}")
                    if link_id not in outgoing_connections:
                        outgoing_connections[link_id] = (connection, slice, queue_id)
                except ValueError:
                    continue
            if not slices:
                # If the packet does not belong to any slice, return all the outgoing connections that are not part of a slice
                if not self.link_to_slice_dict[link_id]:
                    logging.info(f"[get_links_for_slices] No slice found for link: {link_id}, setting queue_id to 0")
                    outgoing_connections[link_id] = (connection, None, 0)

        return outgoing_connections

    def get_l3_packet(self, pkt: Packet) -> Optional[PacketBase]:
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

    def get_packet_protocol(self, pkt: Packet) -> Protocol:
        l3_packet = self.get_l3_packet(pkt)
        if l3_packet is None:
            raise ValueError("No L3 packet found")
        return Protocol.from_id(l3_packet.proto)  # type: ignore
