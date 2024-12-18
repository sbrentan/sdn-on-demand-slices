from typing import Dict

from ryu.base.app_manager import RyuApp
from ryu.topology.api import get_all_switch, get_all_link, get_all_host
from ryu.topology.switches import Switch, Link, Host

from utils._network import Network, Node, NodeType, Connection


class TopologyUtils:

    @staticmethod
    def get_all_switches(app: RyuApp) -> Dict[str, Switch]:
        return {s.dpid: s for s in get_all_switch(app)}
        
    @staticmethod
    def get_all_links(app: RyuApp) -> Dict[str, Link]:
        return {Connection.get_link_id(l): l for l in get_all_link(app)}
    
    @staticmethod
    def get_all_hosts(app: RyuApp) -> Dict[str, Host]:
        return {h.port.dpid: h for h in get_all_host(app)}

    @staticmethod
    def build_network(app: RyuApp) -> Network:
        
        switches = TopologyUtils.get_all_switches(app)
        links = TopologyUtils.get_all_links(app)
        hosts = TopologyUtils.get_all_hosts(app)

        connections = []
        for _, link in links.items():
    
            src_node = Node(
                node_type=NodeType.from_node_id(link.src.dpid),
                node_id=link.src.dpid,
                node_ref=switches[link.src.dpid] if link.src.dpid in switches else hosts[link.src.dpid]
            )
            dst_node = Node(
                node_type=NodeType.from_node_id(link.dst.dpid),
                node_id=link.dst.dpid,
                node_ref=switches[link.dst.dpid] if link.dst.dpid in switches else hosts[link.dst.dpid]
            )
            
            connections.append(Connection(src=(link.src, src_node), dst=(link.dst, dst_node), link_ref=link))
        
        return Network(connections=connections)
