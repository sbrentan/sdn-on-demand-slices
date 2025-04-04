import os
import json
import logging
from typing import Dict, List, Tuple, Optional

from ryu.lib import hub
from ryu.base import app_manager
from ryu.topology import switches
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet.packet import Packet
from ryu.lib.packet import packet, ethernet, ether_types, ipv4
from ryu.app.wsgi import WSGIApplication

from events.topology import TopologyEventHandler
from managers import NetworkManager, SlicesManager, MonitoringManager
from controllers import APIController, GUIController
from utils import SliceUtils, QueueUtils, TopologyUtils, PacketUtils
from common import Network, Node, Slice, Protocol, Queue
from common.constants import OVSDB_TIMEOUT, FlowPriority, DSCP_TAG_VALUE, SKIP_ADD_FLOW_ON_MONITORING

logging.basicConfig(level=logging.DEBUG)


class DynamicSlicingController(app_manager.RyuApp, TopologyEventHandler):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        'wsgi': WSGIApplication,
        'switches': switches.Switches
    }

    slices_manager: SlicesManager
    network_manager: NetworkManager

    mac_to_port: Dict[str, Dict[str, Dict[str, Tuple[int, int]]]]

    def __init__(self, *args, **kwargs):
        logging.info("Initializing DynamicSlicingController")
        super(DynamicSlicingController, self).__init__(*args, **kwargs)

        slices_dict = {}
        slices_file = os.getenv("SLICES_FILE")
        if not slices_file:
            logging.info("SLICES_FILE environment variable not set, not loading slices")
        else:
            logging.info(f"Loading slices from file: {slices_file}")
            with open(slices_file) as f:
                slices_dict = json.load(f)
        
        self.CONF.set_override('ovsdb_timeout', OVSDB_TIMEOUT)

        self.network = Network()

        self.slices_manager = SlicesManager(self.network, slices_dict)

        # Initialize the network handler
        self.network_manager = NetworkManager(self.network)
        self.build_network_greenlet = None

        self.monitoring_manager = MonitoringManager()

        # Register the API and GUI controllers
        wsgi = kwargs['wsgi']
        wsgi.register(APIController, {"slices_manager": self.slices_manager, "monitoring_manager": self.monitoring_manager})
        wsgi.register(GUIController)

        # port, queue_id = self.mac_to_port[dpid][slice_name][mac]
        self.mac_to_port = {}

    def update_topology(self):
        """Abstract method defined in TopologyEventHandler to updated the network topology"""
        logging.info("Updating topology...")

        # Add delay to wait for other simultaneous connections
        if self.build_network_greenlet is not None:
            logging.info("Cancelling previous build network timer")
            hub.kill(self.build_network_greenlet)
        
        def build_network_task():
            logging.info("Topology updated")

            TopologyUtils.build_network(self)
            
            logging.info('Initializing queues...')
            QueueUtils.init_queues()

            self.build_network_greenlet = None
            
        logging.info("Starting build network timer")
        self.build_network_greenlet = hub.spawn_after(1, build_network_task)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER) # type: ignore
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Install the table-miss flow entry
        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        PacketUtils.add_flow(datapath, FlowPriority.TABLE_MISS.value, match, actions)

        match = parser.OFPMatch(eth_type=0x0800, ip_dscp=DSCP_TAG_VALUE >> 2)  # IPv4 with DSCP 32
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        priority = FlowPriority.MONITORED_PACKET.value
        logging.info(f"Adding flow with priority {priority} and match {match}")
        PacketUtils.add_flow(datapath, priority, match, actions)


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER) # type: ignore
    def _packet_in_handler(self, ev):
        if self.build_network_greenlet:
            logging.info("Waiting for network to be built...")
            return
        msg = ev.msg
        datapath = msg.datapath
        in_port = msg.match["in_port"]
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        is_monitored_packet = False
        ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
        if ipv4_pkt:
            dscp_value = (ipv4_pkt.tos)  # Extract DSCP from TOS field
            logging.info("Received IPv4 packet with DSCP value %d", dscp_value)

            is_monitored_packet = dscp_value == 32  # Filter DSCP-tagged packets
            # later, when registering packets for monitoring `add_flow` is not called

        if eth.ethertype != ether_types.ETH_TYPE_IP: # type: ignore
            return
        
        src = eth.src  # type: ignore
        dst = eth.dst  # type: ignore
        dpid = datapath.id

        logging.info(f"---------------------- {self.network.link_to_slice_dict}")

        logging.info("Packet in dpid: %s src: %s dst: %s in_port: %s", dpid, src, dst, in_port)

        switch_id = Node.get_switch_id(dpid)

        in_connection = SliceUtils.get_in_connection(switch_id, in_port)
        if not in_connection:
            logging.error("[ERROR] Could not find in_connection for switch %s port %s", switch_id, in_port)
            return
        logging.info(f"Incoming connection: {in_connection}")

        if is_monitored_packet:
            switch_node = self.network.nodes[Node.get_switch_id(datapath.id)]
            self.monitoring_manager.add_recording_step(switch_node, in_connection)

        # for each slice, set the mac to port for the incoming port
        slices = SliceUtils.get_slices_from_packet(switch_id, pkt, in_connection)

        # Set port for mac and slice for sender in each slice
        for slice in slices:
            slice_name = Slice.get_slice_id(slice)
            result = self._get_port_for_mac_and_slice(switch_id, Slice.get_slice_id(slice), src)
            if not result:
                queue = in_connection.get_queue_for_slice(slice)
                self._set_port_for_mac_and_slice(switch_id, slice_name, src, in_port, queue)
                logging.info(f"Updated routing for sender: {src} -> {in_port} (queue {queue}) in slice {slice_name}")

        # check if the packet belongs to a slice and send it to the corresponding port
        for slice in slices:
            result = self._get_port_for_mac_and_slice(switch_id, Slice.get_slice_id(slice), dst)
            if result:
                out_port, queue_id = result
                # send packet and add flow
                match_conditions = self._get_match_conditions_for_slice(slice, pkt, in_port)
                actions = [
                    datapath.ofproto_parser.OFPActionSetQueue(queue_id),
                    datapath.ofproto_parser.OFPActionOutput(out_port)
                ]
                match = datapath.ofproto_parser.OFPMatch(**match_conditions)
                if not SKIP_ADD_FLOW_ON_MONITORING or not is_monitored_packet:
                    PacketUtils.add_flow(datapath, FlowPriority.DEFAULT.value, match, actions)
                elif is_monitored_packet:
                    out_connection = [c for c in self.network.node_connections[switch_id] if c.is_host_connection and c.host_mac == dst]
                    if out_connection:
                        out_connection = out_connection[0]
                        logging.info("Packet is monitored and is a host connection, adding additional registered step")
                        host_node = self.network.nodes[Node.get_host_id(out_connection.host_mac)]
                        self.monitoring_manager.add_recording_step(host_node, out_connection)
                PacketUtils.send_package(msg, datapath, in_port, actions)
                logging.info(f"Packet sent to slice {Slice.get_slice_id(slice)} from port {in_port} to port {out_port} to queue {queue_id}")
                return

        logging.info("Packet not yet mapped to any slice")
        
        if slices:
            logging.info(f"Packet belongs to slices: {slices}")
        else:
            logging.info("Packet does not belong to any slice")
        
        outgoing_queues = QueueUtils.get_queues_for_slices(switch_id, slices, in_connection, pkt)
        logging.info(f"Outgoing queues: {outgoing_queues}")

        if outgoing_queues:
            actions = []
            for link_id, queue in outgoing_queues.items():

                # determine output port for the connection 
                out_port = queue.determine_out_port(dpid)
                
                # set the queue for the output port, and forward the packet
                actions.append(datapath.ofproto_parser.OFPActionSetQueue(queue.queue_id))
                actions.append(datapath.ofproto_parser.OFPActionOutput(out_port))
               
                slice_name = Slice.get_slice_id(queue.slice)
                logging.info(f"Packet sent on {link_id} from port {in_port} to port {out_port} ({slice_name}) to queue {queue.queue_id} in FLOODING mode")
                
            # set the match for the packet
            match_conditions = self._get_match_conditions_for_packet(pkt, in_port, slices)
            match = datapath.ofproto_parser.OFPMatch(**match_conditions)
            
            # add the flow to the switch
            priority = FlowPriority.FLOODING.value
            if len(outgoing_queues) == 1:
                connection = list(outgoing_queues.values())[0].connection
                if connection.is_host_connection and connection.host_mac == dst:
                    priority = FlowPriority.DEFAULT.value
                    logging.info("Packet reached final destination, setting priority to DEFAULT")
                    if is_monitored_packet:
                        logging.info("Packet is monitored and is a host connection, adding additional registered step")
                        host_node = self.network.nodes[Node.get_host_id(connection.host_mac)]
                        self.monitoring_manager.add_recording_step(host_node, connection)
            if not SKIP_ADD_FLOW_ON_MONITORING or not is_monitored_packet:
                PacketUtils.add_flow(datapath, priority, match, actions)
            
            # flood the packet to all specified connections (after adding flows) 
            PacketUtils.send_package(msg, datapath, in_port, actions)
        else:
            logging.info("No outgoing connections found for the packet, DROPPING it")
            drop_match = datapath.ofproto_parser.OFPMatch(**self._get_match_conditions_for_packet(pkt, in_port, slices))
            if not SKIP_ADD_FLOW_ON_MONITORING or not is_monitored_packet:
                PacketUtils.add_flow(datapath, FlowPriority.DROP.value, drop_match, [])

    def _get_port_for_mac_and_slice(self, switch_id: str, slice_name: str, mac: str) -> Optional[Tuple[int, int]]:
        switch_slices = self.mac_to_port.get(switch_id, None)
        if switch_slices:
            slice_macs = switch_slices.get(slice_name, None)
            if slice_macs:
                return slice_macs.get(mac, None)
        return None

    def _set_port_for_mac_and_slice(self, switch_id: str, slice_name: str, mac: str, port: int, queue: Queue):
        if switch_id not in self.mac_to_port:
            self.mac_to_port[switch_id] = {}
        if slice_name not in self.mac_to_port[switch_id]:
            self.mac_to_port[switch_id][slice_name] = {}
        logging.info(f"Setting port {port} for mac {mac} in slice {slice_name} for switch {switch_id}")
        self.mac_to_port[switch_id][slice_name][mac] = (port, queue.queue_id)
    
    def _get_match_conditions_for_slice(self, slice: Optional[Slice], pkt: Packet, in_port: Optional[int] = None, invert_src_dst: bool = False) -> Dict:
        
        eth_header = pkt.get_protocol(ethernet.ethernet)
        l3_packet = SliceUtils.get_l3_packet(pkt)
        pkt_protocol = Protocol.from_id(l3_packet.proto) if l3_packet else None  # type: ignore
        l4_packet = SliceUtils.get_l4_packet(pkt, pkt_protocol)
        
        conditions = {
            "eth_dst": eth_header.dst if not invert_src_dst else eth_header.src, # type: ignore
            "eth_type": ether_types.ETH_TYPE_IP,
        }
        if in_port:
            conditions["in_port"] = in_port
        if slice:
            if slice.rules["allowed_protocols"] and pkt_protocol:
                if pkt_protocol not in slice.rules["allowed_protocols"]:
                    logging.info(f"[ERROR] Protocol {pkt_protocol} not allowed for slice {slice.id}")
                conditions["ip_proto"] = pkt_protocol.protocol_id
        if slice and l4_packet:
            if slice.rules["allowed_ports"]:
                dst_port = l4_packet.dst_port if not invert_src_dst else l4_packet.src_port  # type: ignore
                if dst_port not in slice.rules["allowed_ports"]:
                    logging.info(f"[ERROR] Port {dst_port} not allowed for slice {slice.id}")
                elif pkt_protocol in [Protocol.UDP, Protocol.TCP]:
                    conditions.update({("udp_dst" if pkt_protocol == Protocol.UDP else "tcp_dst"): dst_port})
            if slice.rules["allowed_services"]:
                dst_ip = l3_packet.dst if not invert_src_dst else l3_packet.src  # type: ignore
                src_ip = l3_packet.src if not invert_src_dst else l3_packet.dst  # type: ignore
                if dst_ip not in slice.rules["allowed_services"] and src_ip not in slice.rules["allowed_services"]:
                    logging.info(f"[ERROR] IP {dst_ip} not allowed for slice {slice.id}")
                else:
                    dst_port = l4_packet.dst_port if not invert_src_dst else l4_packet.src_port  # type: ignore
                    src_port = l4_packet.src_port if not invert_src_dst else l4_packet.dst_port  # type: ignore
                    if src_ip in slice.rules["allowed_services"]:
                        allowed_ports = slice.rules["allowed_services"][src_ip]
                        if src_port not in allowed_ports:
                            logging.info(f"[ERROR] SRC Port {src_port} not allowed for slice {slice.id}")
                        elif pkt_protocol in [Protocol.UDP, Protocol.TCP]:
                            conditions.update({("udp_src" if pkt_protocol == Protocol.UDP else "tcp_src"): src_port})
                            conditions.update({"eth_src": eth_header.src if not invert_src_dst else eth_header.dst})  # type: ignore
                    if dst_ip in slice.rules["allowed_services"]:
                        allowed_ports = slice.rules["allowed_services"][dst_ip]
                        if dst_port not in allowed_ports:
                            logging.info(f"[ERROR] DST Port {dst_port} not allowed for slice {slice.id}")
                        elif pkt_protocol in [Protocol.UDP, Protocol.TCP]:
                            conditions.update({("udp_dst" if pkt_protocol == Protocol.UDP else "tcp_dst"): dst_port})
        logging.info(f"[_get_match_conditions_for_slice] Match conditions for slice {Slice.get_slice_id(slice)}: {json.dumps(conditions, indent=4)}")
        return conditions

    def _get_match_conditions_for_packet(self, pkt: Packet, in_port: int, slices: List[Slice]) -> Dict:
        eth_header = pkt.get_protocol(ethernet.ethernet)
        l3_packet = SliceUtils.get_l3_packet(pkt)
        pkt_protocol = Protocol.from_id(l3_packet.proto) if l3_packet else None  # type: ignore
        
        conditions = {
            "in_port": in_port,
            "eth_dst": eth_header.dst,  # type: ignore
            "eth_type": ether_types.ETH_TYPE_IP,
            "eth_src": eth_header.src,  # type: ignore
        }
        if pkt_protocol:
            conditions["ip_proto"] = pkt_protocol.protocol_id
        if l3_packet:
            src = l3_packet.src  # type: ignore
            dst = l3_packet.dst  # type: ignore
            conditions["ipv4_src"] = src
            conditions["ipv4_dst"] = dst
            if pkt_protocol in [Protocol.UDP, Protocol.TCP]:
                l4_packet = SliceUtils.get_l4_packet(pkt, pkt_protocol)
                # assuming the slices are active and are the incoming packet slices
                logging.info(f"[_get_match_condictions_for_packet] Slices: {slices}")
                logging.info(f"[_get_match_condictions_for_packet] {[s.rules['allowed_ports'] for s in slices]}")
                logging.info(f"[_get_match_condictions_for_packet] {[s.rules['allowed_services'] for s in slices]}")
                if not slices or any([s.rules['allowed_ports'] for s in slices]) or any([s.rules["allowed_services"] and dst in s.rules["allowed_services"] for s in slices]):
                    dst_port = l4_packet.dst_port  # type: ignore
                    conditions.update({("udp_dst" if pkt_protocol == Protocol.UDP else "tcp_dst"): dst_port})
                if not slices or any([s.rules["allowed_services"] and src in s.rules["allowed_services"] for s in slices]):
                    src_port = l4_packet.src_port  # type: ignore
                    conditions.update({("udp_src" if pkt_protocol == Protocol.UDP else "tcp_src"): src_port})
            logging.info(f"[_get_match_condictions_for_packet] Match conditions for packet: {json.dumps(conditions, indent=4)}")
        return conditions


app_manager.require_app('ryu.app.rest_qos') # Needed for managing queues
app_manager.require_app('ryu.app.rest_conf_switch') # Needed for updating ovdb address
