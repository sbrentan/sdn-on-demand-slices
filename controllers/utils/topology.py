import logging
from typing import Dict

from ryu.base.app_manager import RyuApp
from ryu.topology.api import get_all_switch, get_all_link, get_all_host
from ryu.topology.switches import Switch, Link, Host

from utils._network import Network, Node, NodeType, Connection


class TopologyUtils:

    @staticmethod
    def get_all_switches(app: RyuApp) -> Dict[str, Switch]:
        # logging.info("Switches: %s", [vars(s) for s in get_all_switch(app)])
        # Map Datapath ID to Switch object 
        return { "s" + str(s.dp.id): s for s in get_all_switch(app)}
        
    @staticmethod
    def get_all_links(app: RyuApp) -> Dict[str, Link]:
        # logging.info("Links: %s", [vars(s) for s in get_all_link(app)])
        return {Connection.get_link_id(l): l for l in get_all_link(app)}
    
    @staticmethod
    def get_all_hosts(app: RyuApp) -> Dict[str, Host]:
        # logging.info("Hosts: %s", [vars(s) for s in get_all_host(app)])
        return {h.port.dpid: h for h in get_all_host(app)} # probably wrong

    @staticmethod
    def build_network(app: RyuApp) -> Network:
        
        logging.info("Building network...")
        logging.info("App info: %s", app)
        switches = TopologyUtils.get_all_switches(app)
        logging.info(f"Switches: {switches}")
        links = TopologyUtils.get_all_links(app) # returns only the links between switches
        logging.info(f"Links: {links}")
        # hosts = TopologyUtils.get_all_hosts(app)
        # logging.info(f"Hosts: {hosts}")

        connections = []
        for idx, link in links.items():

            logging.info("Link %s", idx)
            logging.info("SRC: %s", vars(link.src))
            logging.info("DST: %s", vars(link.dst))

            src_node_id = "s" + str(link.src.dpid)
            dst_node_id = "s" + str(link.dst.dpid)
    
            src_node = Node(
                node_type=NodeType.SWITCH,
                node_id=src_node_id,
                node_ref=switches[src_node_id]
            )
            dst_node = Node(
                node_type=NodeType.SWITCH,
                node_id=dst_node_id,
                node_ref=switches[dst_node_id] 
            )
            
            connections.append(Connection(src=(link.src, src_node), dst=(link.dst, dst_node), link_ref=link))
        
        # TODO: another for loop to iterate over hosts if necessary
        
        return Network(connections=connections)
