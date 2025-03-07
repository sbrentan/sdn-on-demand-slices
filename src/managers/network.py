import logging
import httpx

from common import Network
from common.constants import CONTROLLER_IP, CONTROLLER_PORT, FlowPriority
from utils.packet import PacketUtils

from ryu.topology.switches import Switch


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

    @staticmethod
    def delete_flows(switch: Switch):
        # curl -X DELETE http://localhost:8080/stats/flowentry/clear/1
        dpid = switch.dp.id
        url = f"http://{CONTROLLER_IP}:{CONTROLLER_PORT}/stats/flowentry/clear/{dpid}"
        
        try:
            logging.info(f"Deleting flows for switch {dpid}")
            response = httpx.request(
                method="DELETE",
                url=url,
            )
            response_status = response.status_code  # Get the status code of the response
            
            if response_status == 200:
                return True
            
        except Exception as e:
            # Handle any other exceptions
            logging.error(f"Exception [delete flows]: {str(e)}")
            return None, str(e)
        
        # TODO: move to packet utils??
        match = switch.dp.ofproto_parser.OFPMatch()
        ofproto = switch.dp.ofproto
        parser = switch.dp.ofproto_parser
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        PacketUtils.add_flow(switch.dp, FlowPriority.TABLE_MISS.value, match, actions)

        return False
