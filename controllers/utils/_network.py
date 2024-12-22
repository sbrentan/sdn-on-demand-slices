from __future__ import annotations
import logging

from enum import Enum
from dataclasses import dataclass

from ryu.topology.switches import Switch, Link, Host, Port

# switches -> [Switch({dp: any, ports: []}), ...]
# links -> [{src: Port, dst: Port}, ...]
# ports -> [{dpid: any, port_no: any, hw_addr: any, name: any}, ...]


class NodeType(Enum):

    HOST = "Host"
    SWITCH = "Switch"

    @staticmethod
    def from_node_id(node_id: str) -> NodeType:
        # return NodeType.HOST
        logging.info("From node id: %s", node_id)
        if node_id.startswith("h"):
            return NodeType.HOST
        elif node_id.startswith("s"):
            return NodeType.SWITCH
        else:
            raise ValueError(f"Unknown node type for node_id: {node_id}")


@dataclass
class Node:

    node_type: NodeType
    node_id: str
    node_ref: Switch | Host

    @staticmethod
    def get_node_id(node_ref: Switch | Host) -> str:
        if isinstance(node_ref, Switch):
            return f"s{node_ref.dp.id}"
        # elif isinstance(node_ref, Host):
        #     return f"h{node_ref.mac}"
        raise ValueError(f"Unknown node type for node_ref: {node_ref}")

    def __repr__(self) -> str:
        return f"{self.node_type.value}({self.node_id})"

    def __str__(self) -> str:
        return self.__repr__()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return NotImplemented
        
        return self.node_id == other.node_id


@dataclass
class Connection:
    
    src: tuple[Port, Node]
    dst: tuple[Port, Node]
    link_ref: Link

    @staticmethod
    def get_link_id(link: Link) -> str:
        first_port_id = link.src.dpid if link.src.dpid < link.dst.dpid else link.dst.dpid
        second_port_id = link.dst.dpid if link.src.dpid < link.dst.dpid else link.src.dpid
        return f"s{first_port_id}-s{second_port_id}"

    @property
    def link_id(self) -> str:
        return self.get_link_id(self.link_ref)

    def __repr__(self) -> str:
        return f"{self.src[1]}:{self.src[0]} -> {self.dst[1]}:{self.dst[0]}"

    def __str__(self) -> str:
        return self.__repr__()


@dataclass
class Network:

    connections: list[Connection]

    def __repr__(self) -> str:
        return f"Network({self.connections})"

    def __str__(self) -> str:
        return self.__repr__()
