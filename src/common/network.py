from __future__ import annotations

import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Any, Dict, Callable

from ryu.topology.switches import Switch, Link, Host, Port

from .slice import Slice

# switches -> [Switch({dp: any, ports: []}), ...]
# links -> [{src: Port, dst: Port}, ...]
# ports -> [{dpid: any, port_no: any, hw_addr: any, name: any}, ...]


class NodeType(Enum):

    HOST = "Host"
    SWITCH = "Switch"
        
    def __str__(self):
        return self.value
    
    def __repr__(self):
        return f'"{self.value}"'


@dataclass
class Node:

    node_type: NodeType
    node_id: str
    node_ref: Switch | Host
    name: Optional[str] = None

    def __post_init__(self):
        if self.node_type == NodeType.HOST and not isinstance(self.node_ref, Host):
            raise ValueError("Invalid node reference for host")
        if self.node_type == NodeType.SWITCH and not isinstance(self.node_ref, Switch):
            raise ValueError("Invalid node reference for switch")
        if not self.name:
            self.name = f"{self.node_type} {self.node_id}"

    @property
    def ref_id(self) -> str:
        return self.get_node_id(self.node_ref)

    @staticmethod
    def get_switch_id(datapath_id: int) -> str:
        return "s" + str(datapath_id)

    @staticmethod
    def get_host_id(mac: str) -> str:
        return "h" + mac

    @staticmethod
    def get_node_id(node_ref: Switch | Host) -> str:
        if isinstance(node_ref, Switch):
            return Node.get_switch_id(node_ref.dp.id)
        elif isinstance(node_ref, Host):
            return Node.get_host_id(node_ref.mac)
        raise ValueError(f"Unknown node type: {node_ref}")

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
    link_ref: Optional[Link]
    queues: List[Any]

    def __post_init__(self):
        if self.dst[1].node_type == NodeType.HOST:
            raise ValueError("Destination node cannot be a host")

    @property
    def link_id(self) -> str:
        return self.get_link_id(self)

    @property
    def is_host_connection(self) -> bool:
        return self.src[1].node_type == NodeType.HOST

    @property
    def host_mac(self) -> str:
        if not self.src or not self.src[1] or not isinstance(self.src[1].node_ref, Host):
            raise ValueError("Invalid source node for host connection")
        return self.src[1].node_ref.mac

    @staticmethod
    def get_link_id(connection: Connection | Link) -> str:
        if isinstance(connection, Connection):
            node_ids = [connection.dst[1].node_id, connection.src[1].node_id]
        elif isinstance(connection, Link):
            node_ids = [Node.get_switch_id(connection.dst.dpid), Node.get_switch_id(connection.src.dpid)]
        else:
            raise ValueError("Unknown connection type")
        node_ids.sort()
        return "-".join(node_ids)

    def get_queue_for_slice(self, slice: Any) -> Any:  # Cannot define type of slice as it is a circular import
        for queue in self.queues:
            if queue.slice == slice:
                return queue
        raise ValueError(f"No queue found for slice: {slice}")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Connection):
            return NotImplemented
        
        return self.link_id == other.link_id

    def __repr__(self) -> str:
        return f"{self.src[1]}:{self.src[0]} -> {self.dst[1]}:{self.dst[0]}"

    def __str__(self) -> str:
        return self.__repr__()


class Network:
    __instance = None

    switches: Dict[str, Switch]
    links: Dict[str, Link]
    hosts: Dict[str, Host]
    nodes: Dict[str, Node]
    connections: List[Connection]

    update_events: List[Callable]

    node_connections: Dict[str, List[Connection]]
    link_to_slice_dict: Dict[str, List[Slice]]

    def __init__(self, switches=None, links=None, hosts=None, connections=None, nodes=None):
        self.switches = switches if switches else {}
        self.links = links if links else {}
        self.hosts = hosts if hosts else {}
        self.connections = connections if connections else []
        self.nodes = nodes if nodes else {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "switches": {k: v.to_dict() for k, v in self.switches.items()},
            "links": {k: v.to_dict() for k, v in self.links.items()},
            "hosts": {k: v.to_dict() for k, v in self.hosts.items()}
        }
    
    def add_update_event(self, event: Callable):
        logging.info(f"Adding update event: {event}")
        self.update_events.append(event)

    def get_instance(self) -> Network:
        if self.__instance is None:
            raise ValueError("Network instance not initialized")
        return self.__instance

    def __new__(cls, **kwargs) -> Network:
        if cls.__instance is None:
            cls.__instance = super().__new__(cls, **kwargs)
        else:
            for key, value in kwargs.items():
                setattr(cls.__instance, key, value)
        for event in cls.__instance.update_events:
            logging.info(f"Calling update event: {event.__name__}")
            event()
        return cls.__instance

    def __repr__(self) -> str:
        return f"Network({len(self.connections)} connections)"

    def __str__(self) -> str:
        return self.__repr__()
