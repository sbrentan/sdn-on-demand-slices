import logging
import json
import httpx  # type: ignore
from typing import Dict, List, Tuple

from ryu.base import app_manager
from ryu.topology import switches
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import dpid as dpid_lib
from ryu.lib.packet import packet, ethernet, ether_types, udp, tcp, icmp, ipv4
from ryu.app.wsgi import WSGIApplication

from common import CommonController
from api_controller import APIController
from utils.topology import TopologyUtils, Connection, Node
from utils.slice import Protocol
from utils.slice import Slice
from utils.constants import CONTROLLER_INSTANCE_NAME, CONTROLLER_IP, CONTROLLER_PORT

class DynamicSlicingController(CommonController):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        'wsgi': WSGIApplication,
        'switches': switches.Switches
    }

    def __init__(self, *args, **kwargs):
        logging.info("Initializing DynamicSlicingController")
        super(DynamicSlicingController, self).__init__(*args, **kwargs)
        self.network = None  # Placeholder for DynamicSlicingTopology instance TODO: is this necessary?
        
        wsgi = kwargs['wsgi']
        wsgi.register(APIController, {CONTROLLER_INSTANCE_NAME: self})


        # TODO: Load the configuration of the network from get_all_switch/get_all_link (handle also topology changes)

        self.slices = [
            Slice(name="slice1", switches=["s1", "s2", "s4"], bandwidth=9000000000, rules={
                "allowed_ports": [9999, 9998],
                "allowed_protocols": [Protocol.UDP.value],
            }),
            Slice(name="slice2", switches=["s1", "s2", "s4"], bandwidth=1000000000, rules={
                "allowed_ports": None,
                "allowed_protocols": [Protocol.TCP.value, Protocol.ICMP.value],
            }),
        ]
        logging.info("slices: " + str(self.slices))

        self.link_to_slice_dict: Dict[str, List[Slice]] = {}
        self.switch_connections: Dict[str, List[Connection]] = {}

        # generation of links
        # loops?
        # generation of flows

    def create_queues(self, dpid, port_name, queues) -> Tuple:
        dpid_str = dpid_lib.dpid_to_str(dpid)
        url = f"http://{CONTROLLER_IP}:{CONTROLLER_PORT}/qos/queue/{dpid_str}"
        
        # Prepare the data to be sent in the POST request
        data = {
            "port_name": port_name.decode("utf-8"),
            "type": "linux-htb",
            "queues": queues
        }
        
        # str(a)[2:-1]
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

        self.link_to_slice_dict = {}
        self.switch_connections = {}

        # TODO: Initialize the data structures to store the slices
        logging.info("Initializing network")
        self.network = TopologyUtils.build_network(self)
        logging.info("network: " + str(self.network))

        for slice in self.slices:
            for connection in self.network.connections:
                connection_id = Connection.get_link_id(connection.link_ref)
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
        
        for connection in self.network.connections:
            src_dpid = connection.src[0].dpid
            dst_dpid = connection.dst[0].dpid
            src_port = connection.src[0].name
            dst_port = connection.dst[0].name

            connection_id = Connection.get_link_id(connection.link_ref)
            # if connection_id in self.link_to_slice_dict and len(self.link_to_slice_dict[connection_id]) > 1:
                # TODO: manage the case when a previous active slice is removed and the queues should be deleted anyway
            status, result = self.delete_queues(src_dpid, src_port)
            logging.info(f"self.delete_queues for connection ({connection}) src {src_dpid} {src_port}: {status} {result}")
            status, result = self.delete_queues(dst_dpid, dst_port)
            logging.info(f"self.delete_queues for connection ({connection}) dst {dst_dpid} {dst_port}: {status} {result}")

            # # self.queues = [{"min_rate": "100000"}, {"min_rate": "200000", "max_rate": "500000"}]
            # queues = []
            # for slice in self.link_to_slice_dict.get(connection_id, []):
            #     queues.append({"min_rate": str(slice.bandwidth), "max_rate": str(slice.bandwidth)})
            # status, result = create_queues(src_dpid, src_port, queues, 1000000)
            # logging.info(f"create_queues for connection ({connection}) src {src_dpid} {src_port}: {status} {result}")

        for _, switch in TopologyUtils.switches.items():
            node_id = Node.get_node_id(switch)
            switch_conn = self.switch_connections.get(node_id, [])
            for conn in switch_conn:
                port_name = conn.src[0].name if conn.src[0].dpid == switch.dp.id else conn.dst[0].name
                connection_id = Connection.get_link_id(conn.link_ref)
                if connection_id in self.link_to_slice_dict and len(self.link_to_slice_dict[connection_id]) > 1:
                    queues = []
                    for slice in self.link_to_slice_dict[connection_id]:
                        queues.append({"min_rate": str(slice.bandwidth), "max_rate": str(slice.bandwidth)})
                    status, result = self.create_queues(switch.dp.id, port_name, queues)
                    logging.info(f"create_queues for switch {switch.dp.id} port {port_name}: {status} {result}")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER) # type: ignore
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install the table-miss flow entry.
        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        self.add_flow(datapath, 0, match, actions)

        # TODO: install the queues
        
        dpid = dpid_lib.dpid_to_str(datapath.id)
        ovsdb_addr = f"tcp:{CONTROLLER_IP}:6632"
        httpx.request(
            "PUT",
            f'http://{CONTROLLER_IP}:{CONTROLLER_PORT}/v1.0/conf/switches/{dpid}/ovsdb_addr', 
            data=f'"{ovsdb_addr}"'  # type: ignore
        )

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER) # type: ignore
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        in_port = msg.match["in_port"]
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth.ethertype == ether_types.ETH_TYPE_LLDP: # type: ignore
            return

        src = eth.src  # type: ignore
        dst = eth.dst  # type: ignore
        dpid = datapath.id

        self.logger.info("Packet in dpid: %s src: %s dst: %s in_port: %s", dpid, src, dst, in_port)        
        
        switch_id = f"s{dpid}"
        if switch_id not in self.switch_connections:
            logging.info(f"Switch {switch_id} not in switch_connections [{self.switch_connections}]")
            return
        connections = self.switch_connections[switch_id]
        
        # Redirecting to first connection satistying the filters
        no_slice_connections = []
        match = None
        queue_id = None
        outport = None
        logging.info(f"Checking connections for switch {switch_id}: {connections}")
        for connection in connections:
            connection_id = Connection.get_link_id(connection.link_ref)
            slices = self.link_to_slice_dict.get(connection_id, [])
            if len(slices) == 0:
                logging.info(f"No slices for connection {connection_id}")
                no_slice_connections.append(connection)
            else:
                # Pick the first slice that satisfies the rules TODO: implement a priority system for multiple matches?
                logging.info(f"Checking slices for connection {connection_id}")
                logging.info(f"Slices: {slices}")
                for idx_slice, slice in enumerate(slices):
                    logging.info(f"Checking slice {slice.name}")

                    # TODO: what if the packet is not IP?
                    if not eth.ethertype == ether_types.ETH_TYPE_IP:  # type: ignore
                        continue
                    
                    # check protocol
                    protocol_valid = slice.rules["allowed_protocols"] is None
                    protocol_pkt = None
                    ip_protocol = pkt.get_protocol(ipv4.ipv4).proto  # type: ignore
                    if not protocol_valid:
                        # Determine the transport layer protocol
                        protocol_valid = True
                        if ip_protocol == Protocol.ICMP.protocol_id and Protocol.ICMP.value in slice.rules['allowed_protocols']:  # ICMP
                            self.logger.info("Packet is ICMP, assign to Queue 1")
                        elif ip_protocol == Protocol.TCP.protocol_id and Protocol.TCP.value in slice.rules['allowed_protocols']:  # TCP
                            protocol_pkt = pkt.get_protocol(tcp.tcp)
                            self.logger.info("Packet is TCP, assign to Queue 2")
                        elif ip_protocol == Protocol.UDP.protocol_id and Protocol.UDP.value in slice.rules['allowed_protocols']:  # UDP
                            protocol_pkt = pkt.get_protocol(udp.udp)
                            self.logger.info("Packet is UDP, assign to Queue 3")
                        else:
                            self.logger.info(f"Protocol not in slice: {ip_protocol}")
                            self.logger.info(f"Allowed protocols: {slice.rules['allowed_protocols']}")
                            self.logger.info(f"icmp {Protocol.ICMP.protocol_id} {Protocol.ICMP.value}")
                            self.logger.info(f"tcp {Protocol.TCP.protocol_id} {Protocol.TCP.value}")
                            self.logger.info(f"udp {Protocol.UDP.protocol_id} {Protocol.UDP.value}")
                            continue
                    if not protocol_valid:
                        continue
                    logging.info(f" - Protocol valid: {protocol_valid}")
                    # check port
                    port_valid = slice.rules["allowed_ports"] is None
                    pkt_port = protocol_pkt.dst_port  # type: ignore
                    if not port_valid and protocol_pkt is not None:
                        port_valid = pkt_port in slice.rules["allowed_ports"]
                    if not port_valid:
                        continue
                    logging.info(f" - Port valid: {port_valid}")

                    # If the slice is valid, set the output queue
                    queue_id = idx_slice + 1
                    self.logger.info(f"Packet matched slice {slice.name}, setting queue {queue_id}")
        
                    match = datapath.ofproto_parser.OFPMatch(
                        in_port=in_port,
                        eth_dst=dst,
                        eth_type=ether_types.ETH_TYPE_IP,
                    )
                    if slice.rules["allowed_protocols"] is None:
                        match.set_ip_proto(ip_protocol)
                    if ip_protocol == Protocol.UDP.protocol_id and slice.rules["allowed_ports"] is not None:
                        match.set_udp_dst(pkt_port)
                    
                    logging.info(f"Match: {match}")
                    outport = connection.dst[0].port_no if connection.src[0].dpid == dpid else connection.src[0].port_no
                    logging.info(f"Outport: {outport}")
                    break
            if match is not None:
                break

        if match is None:
            # TODO: manage flooding to non-slice connections
            logging.info(f"No slice matched, flooding to {no_slice_connections}")
            pass
        else:
            logging.info(f"Matched slice, setting flow and sending packet to {outport} with queue {queue_id}")
            actions = [datapath.ofproto_parser.OFPActionSetQueue(queue_id), datapath.ofproto_parser.OFPActionOutput(outport)]
            self.add_flow(datapath, 1, match, actions)
            self._send_package(msg, datapath, in_port, actions)

        # elif dpid not in self.end_swtiches:
        #     out_port = ofproto.OFPP_FLOOD
        #     actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
        #     match = datapath.ofproto_parser.OFPMatch(in_port=in_port)
        #     self.add_flow(datapath, 1, match, actions)
        #     self._send_package(msg, datapath, in_port, actions)

    def add_slice(self, slice_name, bandwidth, output_port):
        pass
    
    def remove_slice(self, slice_name):
        pass

    def load_slices_from_file(self, filename):
        pass

    def save_slices_to_file(self, filename):
        pass

app_manager.require_app('ryu.app.rest_qos') # Needed for managing queues
# app_manager.require_app('ryu.app.rest_topology')
# app_manager.require_app('ryu.app.ofctl_rest')
app_manager.require_app('ryu.app.rest_conf_switch') # Needed for updating ovdb address