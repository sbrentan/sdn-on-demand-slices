from __future__ import annotations

import logging
from typing import List, Optional

from ryu.lib.packet.packet import Packet
from ryu.lib.packet.packet_base import PacketBase
from ryu.lib.packet import ethernet, ipv4, icmp, tcp, udp, ether_types

from common import Slice, Protocol, Connection, Network


class SliceUtils:

    @staticmethod
    def get_in_connection(switch_id: str, in_port: int) -> Optional[Connection]:
        """
        Get the incoming connection of the packet

        Args:
            switch_id (str): ID of the switch where the packet came from (e.g. s1)
            in_port (int): Port number where the packet came from
        
        Returns:
            Connection: Incoming connection of the packet
        """
        network = Network.get_instance()
        logging.info(f"[get_in_connection] Connections: {network.connections}")
        logging.info(f"[get_in_connection] Node connections: {network.node_connections}")
        connections = network.node_connections.get(switch_id, [])
        logging.info(f"[get_in_connection] Switch connections: {connections} for switch {switch_id}")
        for connection in connections:
            src_valid = connection.src[1].node_id == switch_id and connection.src[0].port_no == in_port
            dst_valid = connection.dst[1].node_id == switch_id and connection.dst[0].port_no == in_port
            logging.info(f"[get_in_connection] Checking connection: {connection.src[1].node_id} - {connection.dst[1].node_id} - {connection.src[0].port_no} - {connection.dst[0].port_no} - {in_port} - {switch_id}")
            if src_valid or dst_valid:
                logging.info(f"[get_in_connection] IN Connection: {connection}")
                return connection
        return None

    @staticmethod
    def is_slice_valid_for_pkt(slice: Slice, pkt_protocol: Protocol, pkt: Packet) -> bool:
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
            logging.info(f"[is_slice_valid_for_pkt] Protocol invalid: {pkt_protocol}")
            return False

        if slice.is_port_valid(pkt_protocol, pkt):
            logging.info("[is_slice_valid_for_pkt] Port valid")
        else:
            logging.info(f"[is_slice_valid_for_pkt] Port invalid: {pkt}. Allowed ports: {slice.rules['allowed_ports']}")
            return False

        if SliceUtils.is_services_valid(slice, pkt):
            logging.info("[is_slice_valid_for_pkt] Services valid")
        else:
            logging.info(f"[is_slice_valid_for_pkt] Services invalid: {pkt}")
            return False
                
        return True

    @staticmethod
    def get_slices_from_packet(switch_id: str, pkt: Packet, in_connection: Connection) -> List[Slice]:
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
            pkt_protocol = SliceUtils.get_packet_protocol(pkt)
        except ValueError:
            return []

        result = []
        
        network = Network.get_instance()
        slices = network.link_to_slice_dict.get(in_connection.link_id, [])
        logging.info(f"[get_slice_from_packet] Slices: {slices}")
        for slice in slices:
            if (SliceUtils.is_slice_valid_for_pkt(slice, pkt_protocol, pkt)):
                logging.info(f"[get_slice_from_packet] Slice found: {slice}")
                result.append(slice)
        if not result:
            logging.info("[get_slice_from_packet] No slice found")
        return result

    @staticmethod
    def is_services_valid(slice: Slice, pkt: Packet) -> bool:
        services_valid = True
        if slice.rules["allowed_services"]:
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
            logging.info(f"[is_services_valid] Checking {src} - {src_port} - " + str(slice.rules["allowed_services"]))
            if src in slice.rules["allowed_services"]:
                if src_port in slice.rules["allowed_services"][src]:
                    services_valid = True
            logging.info(f"[is_services_valid] Checking {dst} - {dst_port} - " + str(slice.rules["allowed_services"]))
            if dst in slice.rules["allowed_services"]:
                if dst_port in slice.rules["allowed_services"][dst]:
                    services_valid = True
        return services_valid
    
    @staticmethod
    def get_link_to_slice_dict(skip_active_slices=True) -> dict:
        network = Network.get_instance()

        link_to_slice_dict = {}
        for connection in network.connections:
            connection_id = Connection.get_link_id(connection)
            link_to_slice_dict[connection_id] = []

        for slice in network.slices:
            if skip_active_slices and not slice.active:
                continue
            for connection in network.connections:
                slice_to_add = None
                connection_id = Connection.get_link_id(connection)
                if connection.is_host_connection:
                    if connection.src[1].ref_id in slice.hosts:
                        if slice.id not in [s.id for s in link_to_slice_dict[connection_id]]:
                            slice_to_add = slice
                elif connection.src[1].ref_id in slice.switches and connection.dst[1].ref_id in slice.switches:
                    if slice.id not in [s.id for s in link_to_slice_dict[connection_id]]:
                        slice_to_add = slice
                if slice_to_add and connection_id not in slice.skipped_links:
                    link_to_slice_dict[connection_id].append(slice_to_add)
        return link_to_slice_dict

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

    @staticmethod
    def get_packet_protocol(pkt: Packet) -> Protocol:
        l3_packet = SliceUtils.get_l3_packet(pkt)
        if l3_packet is None:
            raise ValueError("No L3 packet found")
        return Protocol.from_id(l3_packet.proto)  # type: ignore
