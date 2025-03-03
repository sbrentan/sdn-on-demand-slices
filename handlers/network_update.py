from utils.topology import TopologyUtils, Connection
from utils.queue import QueueUtils
from utils.slice import Slice
from utils.constants import NETWORK_UPDATE_TIMEOUT
from ryu.lib import hub
from typing import List

import logging, time

class NetworkHandler:

    network = None
    network_changed = False # Flag to indicate if the network has changed

    def __init__(self, controller_instance):  
        from ryu_app import DynamicSlicingController      
        self.controller_instance: DynamicSlicingController = controller_instance
        # Spawn the background job to monitor when the network is ready
        hub.spawn(self.init_network)

    def init_network(self):
        while not self.network:
            num_hosts = self.controller_instance.connected_hosts
            num_switches = self.controller_instance.connected_switches
            if self.controller_instance.last_event_time:
                time_since_last_event = time.time() - self.controller_instance.last_event_time
                if time_since_last_event >= NETWORK_UPDATE_TIMEOUT:
                
                    logging.info("Timeout with no other update reached...")

                    current_switches = len(TopologyUtils.get_all_switches(self.controller_instance))
                    current_hosts = len(TopologyUtils.get_all_hosts(self.controller_instance))

                    if num_hosts == current_hosts and num_switches == current_switches:
                        logging.info("Number of hosts and switches match...")
                        self.network = TopologyUtils.build_network(self.controller_instance)
                        logging.info("Network: " + str(self.network))
                        self.init_node_connections()

                        for _, switch in TopologyUtils.switches.items():
                            QueueUtils.set_ovsdb_address(switch.dp.id)

                        self.init_slices(self.controller_instance.slices)
                        break
            hub.sleep(NETWORK_UPDATE_TIMEOUT)

    def init_node_connections(self):
        self.controller_instance.node_connections = {}
        for connection in self.network.connections:
            if connection.src[1].ref_id not in self.controller_instance.node_connections:
                self.controller_instance.node_connections[connection.src[1].ref_id] = []
            if connection.dst[1].ref_id not in self.controller_instance.node_connections:
                self.controller_instance.node_connections[connection.dst[1].ref_id] = []
            self.controller_instance.node_connections[connection.src[1].ref_id].append(connection)
            self.controller_instance.node_connections[connection.dst[1].ref_id].append(connection)
        logging.info("node_connections: " + str(self.controller_instance.node_connections))
        self.controller_instance.slice_utils.node_connections = self.controller_instance.node_connections
        self.controller_instance.queue_utils.node_connections = self.controller_instance.node_connections

    def init_slices(self, slices: List[Slice]):
        self.controller_instance.link_to_slice_dict = {}
        for slice in slices:
            if not slice.active:
                continue
            for connection in self.network.connections:
                connection_id = Connection.get_link_id(connection)
                if connection_id not in self.controller_instance.link_to_slice_dict:
                    self.controller_instance.link_to_slice_dict[connection_id] = []
                if connection.is_host_connection:
                    if connection.src[1].ref_id in slice.hosts:
                        if slice.name not in [s.name for s in self.controller_instance.link_to_slice_dict[connection_id]]:
                            self.controller_instance.link_to_slice_dict[connection_id].append(slice)
                elif connection.src[1].ref_id in slice.switches and connection.dst[1].ref_id in slice.switches:
                    if slice.name not in [s.name for s in self.controller_instance.link_to_slice_dict[connection_id]]:
                        self.controller_instance.link_to_slice_dict[connection_id].append(slice)
        logging.info("link_to_slice dicts: " + str(self.controller_instance.link_to_slice_dict))
        self.controller_instance.slice_utils.link_to_slice_dict = self.controller_instance.link_to_slice_dict
        self.controller_instance.queue_utils.link_to_slice_dict = self.controller_instance.link_to_slice_dict
        self.controller_instance.queue_utils.network = self.network
        self.controller_instance.queue_utils.init_queues()
