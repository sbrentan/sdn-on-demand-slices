import logging
import json
import httpx  # type: ignore
from typing import Dict, List, Tuple, Optional

from ryu.base import app_manager
from ryu.topology import switches
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import dpid as dpid_lib
from ryu.lib.packet.packet import Packet
from ryu.lib.packet import packet, ethernet, ether_types, udp, tcp, icmp, ipv4
from ryu.app.wsgi import WSGIApplication

from common import CommonController
from api_controller import APIController
from utils.topology import TopologyUtils, Connection, Node
from utils.slice import Protocol, Slice, SliceUtils
from utils.constants import CONTROLLER_INSTANCE_NAME, CONTROLLER_IP, CONTROLLER_PORT, OVSDB_ADDR, FlowPriority

class DynamicSlicingController(app_manager.RyuApp, CommonController):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        'wsgi': WSGIApplication,
        'switches': switches.Switches
    }

    def __init__(self, *args, **kwargs):
        logging.info("Initializing DynamicSlicingController")
        super(DynamicSlicingController, self).__init__(*args, **kwargs)
        
        wsgi = kwargs['wsgi']
        wsgi.register(APIController, {CONTROLLER_INSTANCE_NAME: self})

        # TODO: Load the configuration of the network from get_all_switch/get_all_link (handle also topology changes)

        self.slices = [
            Slice(name="slice1", switches=["s1", "s2", "s4"], bandwidth=9000, rules={
                "allowed_ports": [9999, 9998],
                "allowed_protocols": [Protocol.UDP.value],
            }),
            Slice(name="slice2", switches=["s1", "s3", "s4"], bandwidth=1000, rules={
                "allowed_ports": None,
                "allowed_protocols": [Protocol.TCP.value, Protocol.ICMP.value],
            }),
        ]
        logging.info("slices: " + str(self.slices))

        self.network_initialized = False
        self.slice_utils: SliceUtils
        self.link_to_slice_dict: Dict[str, List[Slice]] = {}
        self.switch_connections: Dict[str, List[Connection]] = {}

        # port, queue_id = self.mac_to_port[dpid][slice_name][mac]
        self.mac_to_port: Dict[str, Dict[str, Dict[str, Tuple[int, int]]]] = {}

    def create_queues(self, dpid, port_name, queues) -> Tuple:
        dpid_str = dpid_lib.dpid_to_str(dpid)
        url = f"http://{CONTROLLER_IP}:{CONTROLLER_PORT}/qos/queue/{dpid_str}"
        
        # Prepare the data to be sent in the POST request
        data = {
            "port_name": port_name.decode("utf-8"),
            "type": "linux-htb",
            "queues": queues
        }
        
        logging.info(f"URL: {url}, Data: {data}")

        try:
            response = httpx.request(
                method="POST",
                url=url,
                data=json.dumps(data)  # type: ignore
            )
            response_status = response.status_code  # Get the status code of the response
            response_data = response.text  # Read and decode the response

            if response_status == 200:
                return response_status, json.loads(response_data)

        except Exception as e:
            logging.error(f"Exception {e}")
            return None, str(e)
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

    def init_network(self):

        if self.network_initialized:
            return
        self.network_initialized = True

        self.link_to_slice_dict = {}
        self.switch_connections = {}

        # TODO: Initialize the data structures to store the slices
        logging.info("Initializing network")
        self.network = TopologyUtils.build_network(self)
        logging.info("network: " + str(self.network))

        for slice in self.slices:
            for connection in self.network.connections:
                connection_id = Connection.get_link_id(connection)
                if connection_id not in self.link_to_slice_dict:
                    self.link_to_slice_dict[connection_id] = []
                if connection.src[1].node_id in slice.switches and connection.dst[1].node_id in slice.switches:
                    if slice.name not in [s.name for s in self.link_to_slice_dict[connection_id]]:
                        self.link_to_slice_dict[connection_id].append(slice)
        logging.info("link_to_slice dicts: " + str(self.link_to_slice_dict))

        for connection in self.network.connections:
            if connection.src[1].node_id not in self.switch_connections:
                self.switch_connections[connection.src[1].node_id] = []
            if connection.dst[1].node_id not in self.switch_connections:
                self.switch_connections[connection.dst[1].node_id] = []
            self.switch_connections[connection.src[1].node_id].append(connection)
            self.switch_connections[connection.dst[1].node_id].append(connection)
        logging.info("switch_connections: " + str(self.switch_connections))

        self.slice_utils = SliceUtils(self.link_to_slice_dict, self.switch_connections)
        
        for connection in self.network.connections:
            src_dpid = connection.src[0].dpid
            dst_dpid = connection.dst[0].dpid
            src_port = connection.src[0].name
            dst_port = connection.dst[0].name

            # TODO: change the delete_queue logic: unique url DELETE /qos/queue/all to delete all QoS queues
            # TODO: change the delete_rules logic: unique url DELETE /qos/rules/all/all to delete all QoS rules

            connection_id = Connection.get_link_id(connection)
            # if connection_id in self.link_to_slice_dict and len(self.link_to_slice_dict[connection_id]) > 1:
                # TODO: manage the case when a previous active slice is removed and the queues should be deleted anyway
            # status, result = self.delete_queues(src_dpid, src_port)
            # logging.info(f"self.delete_queues for connection ({connection}) src {src_dpid} {src_port}: {status} {result}")
            # status, result = self.delete_queues(dst_dpid, dst_port)
            # logging.info(f"self.delete_queues for connection ({connection}) dst {dst_dpid} {dst_port}: {status} {result}")

        for _, switch in TopologyUtils.switches.items():
            node_id = Node.get_node_id(switch)
            switch_conn = self.switch_connections.get(node_id, [])
            for conn in switch_conn:
                port_name = conn.src[0].name if conn.src[0].dpid == switch.dp.id else conn.dst[0].name
                connection_id = Connection.get_link_id(conn)            # if connection_id in self.link_to_slice_dict and len(self.link_to_slice_dict[connection_id]) > 1:

                # TODO: check default rate limits
                default_queue = {"min_rate": "100000000000", "max_rate": "100000000000"}
                queues = [default_queue]
                if connection_id in self.link_to_slice_dict and len(self.link_to_slice_dict[connection_id]) > 0:
                    for queue_id, slice in enumerate(self.link_to_slice_dict[connection_id]):
                        temp = {"min_rate": str(slice.bandwidth), "max_rate": str(slice.bandwidth)}
                        queues.append(temp)

                logging.info(f"Creating queues for switch {switch.dp.id} port {port_name}: {queues}")
                status, result = self.create_queues(switch.dp.id, port_name, queues)
                # status, result = False, "Not implemented"
                logging.info(f"create_queues for switch {switch.dp.id} port {port_name}: {status} {result}")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER) # type: ignore
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        logging.info("Switch connected: %s", datapath.id)

        # Install the table-miss flow entry
        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        self.add_flow(datapath, FlowPriority.TABLE_MISS.value, match, actions)  # Priority 0 for table-miss

        # Install other flow entries (e.g., forwarding or QoS-related flows)
        # match = parser.OFPMatch()  # Match IPv4 traffic
        # actions = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        # self.add_flow(datapath, 0, match, actions)  # Priority 1 for general forwarding

        # set the ovsdb address
        
        dpid = dpid_lib.dpid_to_str(datapath.id)
        httpx.request(
            "PUT",
            f'http://{CONTROLLER_IP}:{CONTROLLER_PORT}/v1.0/conf/switches/{dpid}/ovsdb_addr', 
            data=f'"{OVSDB_ADDR}"'  # type: ignore
        )

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER) # type: ignore
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        in_port = msg.match["in_port"]
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth.ethertype != ether_types.ETH_TYPE_IP: # type: ignore
            return

        src = eth.src  # type: ignore
        dst = eth.dst  # type: ignore
        dpid = datapath.id


        # TODO:
        # 1. Check if slice.active is correctly implemented
        # 2. Implement slicing for also host connections



        logging.info("Packet in dpid: %s src: %s dst: %s in_port: %s", dpid, src, dst, in_port)

        switch_id = Node.get_switch_id(dpid)

        in_connection = self.slice_utils.get_in_connection(switch_id, in_port)
        if not in_connection:
            logging.info("[ERROR] Could not find in_connection for switch %s port %s", switch_id, in_port)
            return
        logging.info(f"Incoming connection: {in_connection}")

        # for each slice, set the mac to port for the incoming port
        slices = self.slice_utils.get_slices_from_packet(switch_id, pkt, in_connection)
        slices_to_save = slices if not in_connection.is_host_connection else slices + [None]  # this is done so that end switches map also __no_slice mac to ports
        slices_to_save = slices_to_save if slices_to_save else [None]

        for slice_idx, slice in enumerate(slices_to_save):
            slice_id = Slice.get_slice_id(slice)
            queue_id = slice_idx + 1 if slice else 0
            result = self._get_port_for_mac_and_slice(switch_id, slice_id, src)
            if not result:
                self._set_port_for_mac_and_slice(switch_id, slice_id, src, in_port, queue_id)
        
        # check if the packet belongs to a slice and send it to the corresponding port
        for slice in slices:
            result = self._get_port_for_mac_and_slice(switch_id, slice.name, dst)
            if result:
                out_port, queue_id = result
                # send packet and add flow
                actions = [
                    datapath.ofproto_parser.OFPActionSetQueue(queue_id),
                    datapath.ofproto_parser.OFPActionOutput(out_port)
                ]
                match_conditions = self._get_match_conditions_for_slice(slice, pkt, in_port)
                match = datapath.ofproto_parser.OFPMatch(**match_conditions)
                self.add_flow(datapath, FlowPriority.DEFAULT.value, match, actions)
                self._send_package(msg, datapath, in_port, actions)
                logging.info(f"Packet sent to slice {slice.name} from port {in_port} to port {out_port} to queue {queue_id}")
                return

        logging.info("Packet not yet mapped to any slice")
        if slices:
            logging.info(f"Packet belongs to slices: {slices}")
        else:
            logging.info("Packet does not belong to any slice")
        
        outgoing_connections = self.slice_utils.get_links_for_slices(switch_id, slices, in_connection, pkt)
        logging.info(f"Outgoing connections: {outgoing_connections}")

        # TODO: add flow when host is directly connected?

        if outgoing_connections:
            actions = []
            for link_id, (connection, slice, queue_id) in outgoing_connections.items():

                # determine output port for the connection 
                out_port = connection.src[0].port_no if connection.src[0].dpid == dpid else connection.dst[0].port_no
                
                # set the queue for the output port, and forward the packet
                actions.append(datapath.ofproto_parser.OFPActionSetQueue(queue_id))
                actions.append(datapath.ofproto_parser.OFPActionOutput(out_port))
               
                slice_name = slice.name if slice else "-"
                logging.info(f"Packet sent on {link_id} from port {in_port} to port {out_port} ({slice_name}) to queue {queue_id} in FLOODING mode")
                
                # set the match for the slice 
                # match_conditions = self._get_match_conditions_for_slice(slice, pkt, in_port)
                # match = datapath.ofproto_parser.OFPMatch(**match_conditions)
                
                # add the flow to the switch
                # self.add_flow(datapath, FlowPriority.FLOODING, match, slice_actions)
            
            # flood the packet to all specified connections (after adding flows) 
            self._send_package(msg, datapath, in_port, actions)
        else:
            logging.info("No outgoing connections found for the packet, DROPPING it")
            # TODO: send flow to DROP it?

    def _get_port_for_mac_and_slice(self, switch_id: str, slice_name: str, mac: str) -> Optional[Tuple[int, int]]:
        switch_slices = self.mac_to_port.get(switch_id, None)
        if switch_slices:
            slice_macs = switch_slices.get(slice_name, None)
            if slice_macs:
                return slice_macs.get(mac, None)
        return None

    def _set_port_for_mac_and_slice(self, switch_id: str, slice_name: str, mac: str, port: int, queue_id: int = 0):
        if switch_id not in self.mac_to_port:
            self.mac_to_port[switch_id] = {}
        if slice_name not in self.mac_to_port[switch_id]:
            self.mac_to_port[switch_id][slice_name] = {}
        logging.info(f"Setting port {port} for mac {mac} in slice {slice_name} for switch {switch_id}")
        self.mac_to_port[switch_id][slice_name][mac] = (port, queue_id)
    
    def _get_match_conditions_for_slice(self, slice: Slice, pkt: Packet, in_port: int) -> Dict:
        
        eth_header = pkt.get_protocol(ethernet.ethernet)
        l3_packet = self.slice_utils.get_l3_packet(pkt)
        pkt_protocol = Protocol.from_id(l3_packet.proto) if l3_packet else None  # type: ignore
        
        conditions = {
            "in_port": in_port,
            "eth_dst": eth_header.dst, # type: ignore
            "eth_type": ether_types.ETH_TYPE_IP,
        }
        if slice.rules["allowed_protocols"] and pkt_protocol:
            if pkt_protocol not in slice.rules["allowed_protocols"]:
                logging.info(f"[ERROR] Protocol {pkt_protocol} not allowed for slice {slice.name}")
            conditions["ip_proto"] = pkt_protocol.protocol_id
        if slice.rules["allowed_ports"]:
            dst_port = l3_packet.dst_port  # type: ignore
            if dst_port not in slice.rules["allowed_ports"]:
                logging.info(f"[ERROR] Port {dst_port} not allowed for slice {slice.name}")
            if pkt_protocol == Protocol.UDP.value:
                conditions["udp_dst"] = dst_port
            elif pkt_protocol == Protocol.TCP.value:
                conditions["tcp_dst"] = dst_port
        return conditions

app_manager.require_app('ryu.app.rest_qos') # Needed for managing queues
app_manager.require_app('ryu.app.rest_conf_switch') # Needed for updating ovdb address

# app_manager.require_app('ryu.app.rest_topology')
# app_manager.require_app('ryu.app.ofctl_rest')