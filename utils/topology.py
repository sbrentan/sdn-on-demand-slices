import logging
from typing import Dict

from ryu.base.app_manager import RyuApp
from ryu.topology.api import get_all_switch, get_all_link, get_all_host
from ryu.topology.switches import Switch, Link, Host

from utils._network import Network, Node, NodeType, Connection


class TopologyUtils:

    switches: Dict[str, Switch]
    links: Dict[str, Link]
    hosts: Dict[str, Host]
    nodes: Dict[str, Node]

    @staticmethod
    def get_all_switches(app: RyuApp) -> Dict[str, Switch]:
        # logging.info("Switches: %s", [vars(s) for s in get_all_switch(app)])
        # Map Datapath ID to Switch object 
        return { Node.get_switch_id(s.dp.id): s for s in get_all_switch(app)}
        
    @staticmethod
    def get_all_links(app: RyuApp) -> Dict[str, Link]:
        # logging.info("Links: %s", [vars(s) for s in get_all_link(app)])
        return {Connection.get_link_id(l): l for l in get_all_link(app)}
    
    @staticmethod
    def get_all_hosts(app: RyuApp) -> Dict[str, Host]:
        # logging.info("Hosts: %s", [vars(s) for s in get_all_host(app)])
        return { Node.get_host_id(h.mac): h for h in get_all_host(app)}

    @staticmethod
    def build_network(app: RyuApp) -> Network:
        
        logging.info("Building network...")
        logging.info("App info: %s", app)
        switches = TopologyUtils.get_all_switches(app)
        links = TopologyUtils.get_all_links(app) # returns only the links between switches
        hosts = TopologyUtils.get_all_hosts(app)
        nodes = {}

        switches_to_print = {k: v.to_dict() for k, v in switches.items()}
        logging.info(f"Switches: {switches_to_print}")
        hosts_to_print = {k: v.to_dict() for k, v in hosts.items()}
        logging.info(f"Hosts: {hosts_to_print}")

        connections = []
        for idx, link in links.items():

            logging.info("Link %s", idx)
            logging.info("SRC: %s", vars(link.src))
            logging.info("DST: %s", vars(link.dst))

            src_node_id = Node.get_switch_id(link.src.dpid)
            dst_node_id = Node.get_switch_id(link.dst.dpid)
    
            src_node = Node(
                node_type=NodeType.SWITCH,
                node_id=src_node_id,
                node_ref=switches[src_node_id]
            )
            if src_node_id not in nodes:
                nodes[src_node_id] = src_node
            dst_node = Node(
                node_type=NodeType.SWITCH,
                node_id=dst_node_id,
                node_ref=switches[dst_node_id] 
            )
            if dst_node_id not in nodes:
                nodes[dst_node_id] = dst_node
            
            connections.append(Connection(
                src=(link.src, src_node), 
                dst=(link.dst, dst_node), 
                link_ref=link,
                queues=[]
            ))
        
        for host_id, host in hosts.items():
            logging.info("Host %s", host_id)
            logging.info("Switch: %s", host.port.dpid)
            logging.info("IPv4 address: %s", host.ipv4)
            host_node = Node(
                node_type=NodeType.HOST,
                node_id=host_id,
                node_ref=host
            )
            
            if host_id not in nodes:
                nodes[host_id] = host_node
            switch_node_id = Node.get_switch_id(host.port.dpid)
            
            connections.append(Connection(
                src=(host.port, host_node),
                dst=(host.port, Node(node_type=NodeType.SWITCH, node_id=switch_node_id, node_ref=switches[switch_node_id])),
                link_ref=None,  # no link exists between host and switch
                queues=[]
            ))

        TopologyUtils.switches = switches
        TopologyUtils.links = links
        TopologyUtils.hosts = hosts
        TopologyUtils.nodes = nodes
        
        return Network(connections=connections)
