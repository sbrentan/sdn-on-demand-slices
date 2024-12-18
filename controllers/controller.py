from typing import Dict, List

from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, udp, tcp, icmp
from ryu.app.wsgi import WSGIApplication

from controllers.common import CommonController
from controllers.api_controller import APIController
from utils.topology import TopologyUtils, Connection
from utils.slice import Slice


# REST API Constants
CONTROLLER_INSTANCE_NAME = 'dynamic_slicing_controller_api'
BASE_URL = '/network'

class DynamicSlicingController(CommonController):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(DynamicSlicingController, self).__init__(*args, **kwargs)
        self.network = None  # Placeholder for DynamicSlicingTopology instance
        self.wsgi = kwargs['wsgi']
        self.wsgi.register(APIController, {CONTROLLER_INSTANCE_NAME: self})


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
        print("slices:", self.slices)

        # generation of links
        # loops?
        # generation of flows

    def init_network(self):

        # TODO: Initialize the data structures to store the slices
        self.network = TopologyUtils.build_network(self)
        print("network:", self.network)

        self.link_to_slice_dict: Dict[Connection, List[Slice]]

        for connection in self.network.connections:
            self.link_to_slice_dict[connection] = []
            for slice in self.slices:
                connection_in_slice = False
                for switch in slice.switches:
                    if connection.src[0].dpid == switch or connection.dst[0].dpid == switch:
                        connection_in_slice = True
                        break
                if connection_in_slice:
                    self.link_to_slice_dict[connection].append(slice)

        print("link_to_slice dicts:", self.link_to_slice_dict)

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
