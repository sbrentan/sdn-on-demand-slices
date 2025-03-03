import httpx, json, time, logging
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple

from ryu.lib import dpid as dpid_lib
from ryu.lib.packet import ethernet
from ryu.lib.packet.packet import Packet

from utils.topology import Connection, Switch, Network, Node, TopologyUtils
from utils.slice import Slice
from utils.constants import CONTROLLER_IP, CONTROLLER_PORT, OVSDB_ADDR, NETWORK_MAX_RATE

@dataclass
class Queue:

    switch: Switch
    connection: Connection
    queue_id: int
    min_rate: Optional[int] = None
    max_rate: Optional[int] = None
    slice: Optional[Slice] = None

    def __post_init__(self):
        if not self.max_rate:
            self.max_rate = NETWORK_MAX_RATE

    def determine_out_port(self, dpid: int) -> int:
        out_port = self.connection.src[0].port_no if self.connection.src[0].dpid == dpid else self.connection.dst[0].port_no
        return out_port

    # @staticmethod
    # def get_default_queue(switch: Switch, connection: Any, min_rate: int = 100, max_rate: int = 100):
    #     return Queue(switch=switch, connection=connection, queue_id=0, min_rate=min_rate, max_rate=max_rate)
    
    def to_queue_dict(self):
        queue_dict = {}
        if self.min_rate is not None:
            queue_dict["min_rate"] = str(self.min_rate)
        if self.max_rate is not None:
            queue_dict["max_rate"] = str(self.max_rate)
        return queue_dict


class QueueUtils:

    link_to_slice_dict: Dict[str, List[Slice]]
    node_connections: Dict[str, List[Connection]]
    network: Optional[Network]
    
    def __init__(self, network: Optional[Network], link_to_slice_dict: dict, node_connections: dict):
        self.link_to_slice_dict = link_to_slice_dict
        self.node_connections = node_connections
        self.network = network

    def get_queues_for_slices(self, switch_id: str, slices: List[Slice], in_connection: Connection, pkt: Packet) -> Dict[str, Queue]:
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
            pkt (Packet): Packet object

        Returns:
            Dict[str, Queue]: Dict of outgoing queues for the slices
        """
        connections = self.node_connections.get(switch_id, [])
        logging.info(f"[get_links_for_slices] Switch {switch_id} connections: {connections}")
        outgoing_queues: Dict[str, Queue] = {}
        eth_dst = pkt.get_protocol(ethernet.ethernet).dst # type: ignore

        for connection in connections:
            if connection == in_connection:
                continue
            
            link_id = connection.link_id
            logging.info(f"[get_links_for_slices] Connection: {link_id}")

            if connection.is_host_connection:
                if connection.host_mac != eth_dst:
                    logging.info(f"[get_links_for_slices] Skipping host connection: {link_id}")
                    continue

            for slice in slices:
                try:
                    if link_id not in outgoing_queues:
                        queue = connection.get_queue_for_slice(slice)
                        logging.info(f"[get_links_for_slices] Slice found: {slice} with queue_id: {queue.queue_id}")
                        outgoing_queues[link_id] = queue
                except ValueError:
                    logging.info(f"[get_links_for_slices] [ValueError] Slice not found for link: {link_id}")
                    continue
            if connection.is_host_connection and link_id in outgoing_queues:
                # connection.host_mac is equal to eth_dst
                logging.info(f"[get_links_for_slices] Host connection found: {link_id}")
                return {link_id: outgoing_queues[link_id]}
                
            # if not slices and not self.link_to_slice_dict[link_id]:
            #     # If the packet does not belong to any slice and the connection does not have any slice
            #     #     flood the packet to this connection in FLOODING mode in default queue
            #     logging.info(f"[get_links_for_slices] No slice found for link: {link_id}, setting queue_id to 0")
            #     try:
            #         outgoing_queues[link_id] = connection.get_queue_for_slice(None)
            #     except ValueError:
            #         logging.info(f"[get_links_for_slices] [ValueError] Default queue not found for link: {link_id}")
            #         continue
                
        return outgoing_queues

    def init_queues(self):
        
        if self.network is None:
            logging.info("[init_queues] Network is not defined")
            return
        for connection in self.network.connections:
            src_dpid = connection.src[0].dpid
            dst_dpid = connection.dst[0].dpid
            src_port = connection.src[0].name
            dst_port = connection.dst[0].name

            # TODO: change the delete_queue logic: unique url DELETE /qos/queue/all to delete all QoS queues
            # TODO: change the delete_rules logic: unique url DELETE /qos/rules/all/all to delete all QoS rules ??

            connection_id = Connection.get_link_id(connection)
            # if connection_id in self.link_to_slice_dict and len(self.link_to_slice_dict[connection_id]) > 1:
                # TODO: manage the case when a previous active slice is removed and the queues should be deleted anyway
            # status, result = QueueUtils.delete_queues(src_dpid, src_port)
            # logging.info(f"QueueUtils.delete_queues for connection ({connection}) src {src_dpid} {src_port}: {status} {result}")
            # status, result = QueueUtils.delete_queues(dst_dpid, dst_port)
            # logging.info(f"QueueUtils.delete_queues for connection ({connection}) dst {dst_dpid} {dst_port}: {status} {result}")

        for _, switch in TopologyUtils.switches.items():
            node_id = Node.get_node_id(switch)
            switch_connections = self.node_connections.get(node_id, [])
            for connection in switch_connections:
                port_name = connection.src[0].name if connection.src[0].dpid == switch.dp.id else connection.dst[0].name
                connection_id = Connection.get_link_id(connection)

                queues = []
                if connection_id in self.link_to_slice_dict and len(self.link_to_slice_dict[connection_id]) > 0:
                    for queue_id, slice in enumerate(self.link_to_slice_dict[connection_id]):
                        logging.info(f"Creating queue for slice {slice.name} on switch {switch.dp.id} port {port_name}: {queue_id}")
                        queues.append(Queue(
                            switch=switch,
                            connection=connection,
                            queue_id=queue_id,
                            min_rate=slice.min_rate,
                            max_rate=slice.max_rate,
                            slice=slice
                        ))

                # if queues:
                #     logging.info(f"Setting default queue for switch {switch.dp.id} port {port_name}")
                #     queues = [Queue.get_default_queue(switch, connection)] + queues
                # else:
                #     logging.info(f"Adding default queue for switch {switch.dp.id} port {port_name}")
                #     queues.append(Queue.get_default_queue(switch, connection, min_rate=DEFAULT_QUEUE_MIN_RATE, max_rate=DEFAULT_QUEUE_MAX_RATE))

                logging.info(f"Creating queues for switch {switch.dp.id} on port {port_name}")
                status, result = self.create_queues(switch.dp.id, port_name, queues)
                logging.info(f"create_queues for switch {switch.dp.id} port {port_name}: {status} {result}")

                connection.queues = queues

    @staticmethod
    def set_ovsdb_address(dpid):
        dpid_str = dpid_lib.dpid_to_str(dpid)
        response = httpx.request(
            "PUT",
            f'http://{CONTROLLER_IP}:{CONTROLLER_PORT}/v1.0/conf/switches/{dpid_str}/ovsdb_addr', 
            data=f'"{OVSDB_ADDR}"'  # type: ignore
        )
        logging.info(f"Setting OVSDB address for switch {dpid}: {response.status_code} {response.text}")

    @staticmethod
    def create_queues(dpid, port_name, queues: List[Queue], max_retries: int = 5) -> Tuple:

        dpid_str = dpid_lib.dpid_to_str(dpid)
        url = f"http://{CONTROLLER_IP}:{CONTROLLER_PORT}/qos/queue/{dpid_str}"
        
        # Prepare the data to be sent in the POST request
        data = {
            "port_name": port_name.decode("utf-8"),
            "type": "linux-htb",
            "max_rate": str(NETWORK_MAX_RATE),
            "queues": [queue.to_queue_dict() for queue in queues]
        }
        
        logging.info(f"URL: {url}, Data: {json.dumps(data, indent=4)}")

        for i in range(max_retries):            
            try:

                response = httpx.request(
                    method="POST",
                    url=url,
                    data=json.dumps(data),  # type: ignore
                    timeout=10
                )

                response_status = response.status_code
                response_data = json.loads(response.text) 
                logging.info(f"Response: {response_status} {response_data}")

                if response_status == 200 and response_data[0]['command_result']['result'] == 'success':
                    return response_status, response_data
                elif response_status == 200 and response_data[0]['command_result']['details'] == 'ovs_bridge is not exists':
                    QueueUtils.set_ovsdb_address(dpid)

            except Exception as e:
                logging.error(f"Exception {e}")
                time.sleep(2 * (i+1))
                logging.info(f"Retrying to create queues for switch {dpid} port {port_name} (attempt {i + 1})")
        
        return None, ""

    def delete_queues(self, dpid, port_name) -> Tuple:
        dpid_str = dpid_lib.dpid_to_str(dpid)
        url = f"http://{CONTROLLER_IP}:{CONTROLLER_PORT}/qos/queue/{dpid_str}"

        # Prepare the data to be sent in the DELETE request
        data = {"port_name": port_name.decode("utf-8")}
        
        logging.info(f"URL: {url}, Data: {data}")
        
        try:
            response = httpx.request(
                method="DELETE",
                url=url,
                data=json.dumps(data) #type: ignore
            )
            response_status = response.status_code  # Get the status code of the response
            response_data = response.text  # Read and decode the response
            
            if response_status == 200:
                return response_status, json.loads(response_data)
            
        except Exception as e:
            # Handle any other exceptions
            logging.error(f"Exception: {str(e)}")
            return None, str(e)
        return None, ""
