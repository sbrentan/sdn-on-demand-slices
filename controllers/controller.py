import logging
import json
import urllib.request
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
from utils.topology import TopologyUtils, Connection, Node
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
                "allowed_protocols": ["udp"],
            }),
            Slice(name="slice2", switches=["s1", "s3", "s4"], bandwidth=1000000000, rules={
                "allowed_ports": None,
                "allowed_protocols": ["tcp"],
            }),
        ]
        logging.info("slices: " + str(self.slices))

        self.link_to_slice_dict: Dict[str, List[Slice]] = {}
        self.switch_connections: Dict[str, List[Connection]] = {}

        # generation of links
        # loops?
        # generation of flows

    def delete_queueues(self, dpid, port_name):
        pass
        
    def create_queues(self, dpid, port_name, queues):
        url = f"http://{CONTROLLER_IP}:{CONTROLLER_PORT}/qos/queue/{dpid}"
        
        # Prepare the data to be sent in the POST request
        data = {
            "port_name": port_name,
            "type": "linux-htb",
            "queues": queues
        }
        json_data = json.dumps(data).encode('utf-8')  # Convert the dictionary to JSON and encode it
        
        logging.info(f"URL: {url}, Data: {data}")
        
        # Create the request object with the POST method
        request = urllib.request.Request(url, data=json_data, method='POST')
        request.add_header('Content-Type', 'application/json')
        
        try:
            # Send the request and get the response
            with urllib.request.urlopen(request) as response:
                response_data = response.read().decode('utf-8')  # Read and decode the response
                
                # Check the status code in the response
                if response.status == 200:
                    return response.status, json.loads(response_data)  # Return the JSON response if status is 200
                else:
                    return response.status, response_data  # Return the response text for other status codes
        except Exception as e:
            # Handle any other exceptions
            logging.error(f"Exception: {str(e)}")
            return None, str(e)

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


        def delete_queues(dpid, port_name):
            url = f"http://{CONTROLLER_IP}:{CONTROLLER_PORT}/qos/queue/{dpid}"
    
            # Prepare the data to be sent in the DELETE request
            data = {"port_name": port_name}
            json_data = json.dumps(data).encode('utf-8')  # Convert the dictionary to JSON and encode it
            
            logging.info(f"URL: {url}, Data: {data}")
            
            # Create the request object with the DELETE method
            request = urllib.request.Request(url, data=json_data, method='DELETE')
            request.add_header('Content-Type', 'application/json')
            
            try:
                # Send the request and get the response
                with urllib.request.urlopen(request) as response:
                    response_data = response.read().decode('utf-8')  # Read and decode the response
                    return response.status, response_data
            except Exception as e:
                # Handle any other exceptions
                logging.error(f"Exception: {str(e)}")
                return None, str(e)
        
        for connection in self.network.connections:
            src_dpid = connection.src[0].dpid
            dst_dpid = connection.dst[0].dpid
            src_port = connection.src[0].name
            dst_port = connection.dst[0].name

            connection_id = Connection.get_link_id(connection.link_ref)
            # if connection_id in self.link_to_slice_dict and len(self.link_to_slice_dict[connection_id]) > 1:
                # TODO: manage the case when a previous active slice is removed and the queues should be deleted anyway
            status, result = delete_queues(src_dpid, src_port)
            logging.info(f"delete_queues for connection ({connection}) src {src_dpid} {src_port}: {status} {result}")
            status, result = delete_queues(dst_dpid, dst_port)
            logging.info(f"delete_queues for connection ({connection}) dst {dst_dpid} {dst_port}: {status} {result}")

            # # self.queues = [{"min_rate": "100000"}, {"min_rate": "200000", "max_rate": "500000"}]
            # queues = []
            # for slice in self.link_to_slice_dict.get(connection_id, []):
            #     queues.append({"min_rate": str(slice.bandwidth), "max_rate": str(slice.bandwidth)})
            # status, result = create_queues(src_dpid, src_port, queues, 1000000)
            # logging.info(f"create_queues for connection ({connection}) src {src_dpid} {src_port}: {status} {result}")

        for _, switch in TopologyUtils.switches.items():
            node_id = Node.get_node_id(switch.dp.id)
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
        # actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]

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
app_manager.require_app('ryu.app.rest_qos')
# app_manager.require_app('ryu.app.ofctl')
# app_manager.require_app('ryu.app.rest_router')
# app_manager.require_app('ryu.topology.switches', api_style=True)