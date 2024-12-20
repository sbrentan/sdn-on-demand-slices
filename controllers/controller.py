import logging
from typing import Dict, List

from ryu.base import app_manager
from ryu.topology import switches
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, udp, tcp, icmp
from ryu.app.wsgi import WSGIApplication

from common import CommonController
from api_controller import APIController
from utils.topology import TopologyUtils, Connection
from utils.slice import Slice
from utils.constants import CONTROLLER_INSTANCE_NAME

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
            Slice(name="slice1", switches=["s1", "s2", "s4"], rules={
                "allowed_ports": [9999, 9998],
                "allowed_protocols": ["udp"],
            }),
            Slice(name="slice2", switches=["s1", "s3", "s4"], rules={
                "allowed_ports": None,
                "allowed_protocols": ["tcp"],
            }),
        ]
        logging.info("slices: " + str(self.slices))

        # generation of links
        # loops?
        # generation of flows

    def init_network(self):

        # TODO: Initialize the data structures to store the slices
        logging.info("Initializing network")
        self.network = TopologyUtils.build_network(self)
        logging.info("network: " + str(self.network))

        self.link_to_slice_dict: Dict[str, List[Slice]] = {}

        for connection in self.network.connections:
            connection_id = Connection.get_link_id(connection.link_ref)
            self.link_to_slice_dict[connection_id] = []
            for slice in self.slices:
                connection_in_slice = False
                for switch in slice.switches:

                    # TODO: check if this is correct: shouldn't both src and dst be present in the slice?
                    if switch in [connection.src[1].node_id, connection.dst[1].node_id]:
                        connection_in_slice = True
                        break
                    
                if connection_in_slice:
                    self.link_to_slice_dict[connection_id].append(slice)

        logging.info("link_to_slice dicts: " + str(self.link_to_slice_dict))

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

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER) # type: ignore
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        in_port = msg.match["in_port"]
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth.ethertype == ether_types.ETH_TYPE_LLDP: # type: ignore
            return


        # TODO: instruct the switch to set the output queue based on the link_to_slice dict


        src = eth.src  # type: ignore
        dst = eth.dst  # type: ignore
        dpid = datapath.id

        self.logger.info("Packet in dpid: %s src: %s dst: %s in_port: %s", dpid, src, dst, in_port)
        self._handle_packet(msg, datapath, in_port, pkt)
    
    def _handle_packet(self, msg, datapath, in_port, pkt):
        eth = pkt.get_protocol(ethernet.ethernet)
        protocol = pkt.get_protocol(udp.udp) or pkt.get_protocol(tcp.tcp) or pkt.get_protocol(icmp.icmp)
        actions = []

        # Manage what to do with the packet


    def add_slice(self, slice_name, bandwidth, output_port):
        pass
    
    def remove_slice(self, slice_name):
        pass

    def load_slices_from_file(self, filename):
        pass

    def save_slices_to_file(self, filename):
        pass

# app_manager.require_app('ryu.app.rest_topology')
# app_manager.require_app('ryu.app.rest_conf_switch')
# app_manager.require_app('ryu.app.rest_qos')
# app_manager.require_app('ryu.app.ofctl')
# app_manager.require_app('ryu.app.rest_router')
# app_manager.require_app('ryu.topology.switches', api_style=True)