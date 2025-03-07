import logging

from common import Network


class NetworkManager:

    network: Network

    def __init__(self, network: Network):
        self.network = network
        self.network.add_update_event(self.init_node_connections)

    def init_node_connections(self):
        if not self.network:
            logging.error("[INIT NODE CONNECTIONS] Network not initialized yet...")
            return
        logging.info("Initializing node connections...")
        node_connections = {}
        for connection in self.network.connections:
            if connection.src[1].ref_id not in node_connections:
                node_connections[connection.src[1].ref_id] = []
            if connection.dst[1].ref_id not in node_connections:
                node_connections[connection.dst[1].ref_id] = []
            node_connections[connection.src[1].ref_id].append(connection)
            node_connections[connection.dst[1].ref_id].append(connection)
        logging.info("node_connections: " + str(node_connections))
        self.network.node_connections = node_connections
