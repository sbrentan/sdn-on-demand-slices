
"""
ovs-vsctl set port <port_name> qos=@newqos -- \
    --id=@newqos create QoS type=linux-htb other-config:max-rate=10000000 queues:1=@q1 queues:2=@q2 -- \
    --id=@q1 create queue other-config:min-rate=1000000 other-config:max-rate=1000000 -- \
    --id=@q2 create queue other-config:min-rate=9000000 other-config:max-rate=9000000

"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, set_ev_cls
from ryu.lib.ovs import vsctl
from ryu.lib.packet import ethernet, ipv4, tcp, udp
from ryu.ofproto import ether

class QoSController(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(QoSController, self).__init__(*args, **kwargs)
        # Initialize OVSDB client
        self.ovs_vsctl = vsctl.VSCtl()

    def configure_qos(self, bridge_name, max_rate, tcp_share, udp_share):
        """
        Configures QoS on a given OVS bridge.
        """
        # Calculate bandwidth shares
        tcp_rate = int(max_rate * tcp_share)
        udp_rate = int(max_rate * udp_share)
        
        # Connect to the bridge
        self.ovs_vsctl.run_command(['add-br', bridge_name])

        # Create queues
        self.ovs_vsctl.run_command([
            'set', 'port', bridge_name, 
            f'qos=@newqos -- --id=@newqos create QoS type=linux-htb other-config:max-rate={max_rate} '
            f'queues:1=@tcp_queue queues:2=@udp_queue -- --id=@tcp_queue create queue other-config:min-rate={tcp_rate} '
            f'other-config:max-rate={tcp_rate} -- --id=@udp_queue create queue other-config:min-rate={udp_rate} '
            f'other-config:max-rate={udp_rate}'
        ])
        self.logger.info(f"QoS configured on {bridge_name}: TCP={tcp_rate}, UDP={udp_rate}")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """
        Handles incoming packets and assigns them to queues based on their protocol.
        """
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Parse the packet
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        ip = pkt.get_protocol(ipv4.ipv4)

        if not ip:
            return  # Ignore non-IP packets

        # Match on TCP/UDP protocols and install flow rules
        if ip.proto == inet.IPPROTO_TCP:
            actions = [parser.OFPActionSetQueue(1), parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        elif ip.proto == inet.IPPROTO_UDP:
            actions = [parser.OFPActionSetQueue(2), parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        else:
            return  # Ignore non-TCP/UDP packets

        match = parser.OFPMatch(eth_type=ether.ETH_TYPE_IP, ip_proto=ip.proto)
        self.add_flow(datapath, 100, match, actions)

    def add_flow(self, datapath, priority, match, actions):
        """
        Adds a flow to the switch.
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)
        datapath.send_msg(mod)
















from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, set_ev_cls
from ryu.lib.ovs import vsctl
from ryu.lib.packet import packet, ethernet, ipv4
from ryu.ofproto import ether, inet
from ryu.ofproto import ofproto_v1_3
from ryu.app.wsgi import WSGIApplication, ControllerBase, route
from ryu.lib import dpid as dpid_lib

import json
from webob import Response

# QoS REST API Service
QOS_CONTROLLER_INSTANCE_NAME = 'qos_controller_api'

class QoSController(app_manager.RyuApp):
    _CONTEXTS = {'wsgi': WSGIApplication}
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(QoSController, self).__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        self.ovs_vsctl = vsctl.VSCtl()

        # Register REST API Controller
        wsgi.register(QoSRestController, {QOS_CONTROLLER_INSTANCE_NAME: self})

    def check_existing_qos(self, bridge_name):
        """
        Check if the bridge already has a QoS configuration.
        """
        output = self.ovs_vsctl.run_command(['get', 'port', bridge_name, 'qos'])
        return output.strip() != ''

    def configure_qos(self, bridge_name, max_rate, tcp_share, udp_share):
        """
        Configures QoS on a given OVS bridge.
        """

        # Reset existing QoS settings
        self.ovs_vsctl.run_command(['clear', 'port', bridge_name, 'qos'])

        # Calculate bandwidth shares
        tcp_rate = int(max_rate * tcp_share)
        udp_rate = int(max_rate * udp_share)
        
        # Create queues dynamically
        self.ovs_vsctl.run_command([
            'set', 'port', bridge_name, 
            f'qos=@newqos -- --id=@newqos create QoS type=linux-htb other-config:max-rate={max_rate} '
            f'queues:1=@tcp_queue queues:2=@udp_queue -- --id=@tcp_queue create queue other-config:min-rate={tcp_rate} '
            f'other-config:max-rate={tcp_rate} -- --id=@udp_queue create queue other-config:min-rate={udp_rate} '
            f'other-config:max-rate={udp_rate}'
        ])
        self.logger.info(f"QoS configured on {bridge_name}: TCP={tcp_rate}, UDP={udp_rate}")

    def add_flow(self, datapath, priority, match, actions):
        """
        Adds a flow to the switch.
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)
        datapath.send_msg(mod)


class QoSRestController(ControllerBase):
    """
    REST API Controller for managing QoS dynamically.
    """

    def __init__(self, req, link, data, **config):
        super(QoSRestController, self).__init__(req, link, data, **config)
        self.qos_controller = data[QOS_CONTROLLER_INSTANCE_NAME]

    @route('qos', '/qos/configure', methods=['POST'])
    def configure_qos(self, req, **kwargs):
        """
        REST API: Configure QoS dynamically.
        Request Format:
        {
            "bridge": "br0",
            "max_rate": 10000000,
            "tcp_share": 0.1,
            "udp_share": 0.9
        }
        """
        try:
            data = json.loads(req.body)
            bridge = data['bridge']
            max_rate = int(data['max_rate'])
            tcp_share = float(data['tcp_share'])
            udp_share = float(data['udp_share'])

            self.qos_controller.configure_qos(bridge, max_rate, tcp_share, udp_share)
            return Response(status=200, body=json.dumps({"status": "success"}))
        except Exception as e:
            return Response(status=500, body=json.dumps({"status": "error", "details": str(e)}))







from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, set_ev_cls
from ryu.lib.ovs import vsctl
from ryu.lib.packet import packet, ethernet, ipv4
from ryu.ofproto import ether, inet
from ryu.lib import hub

import time
import threading

class DynamicQoSController(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(DynamicQoSController, self).__init__(*args, **kwargs)
        self.ovs_vsctl = vsctl.VSCtl()
        self.bridge_name = "br0"
        self.max_rate = 10000000  # 10 Mbps
        self.tcp_min_rate = 1000000  # 1 Mbps (10%)
        self.udp_min_rate = 9000000  # 9 Mbps (90%)

        # Start traffic monitoring thread
        self.monitor_thread = threading.Thread(target=self.monitor_traffic)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def configure_qos(self):
        """
        Configure initial QoS with guaranteed minimums.
        """
        self.ovs_vsctl.run_command([
            'set', 'port', self.bridge_name,
            f'qos=@newqos -- --id=@newqos create QoS type=linux-htb other-config:max-rate={self.max_rate} '
            f'queues:1=@tcp_queue queues:2=@udp_queue -- --id=@tcp_queue create queue other-config:min-rate={self.tcp_min_rate} '
            f'other-config:max-rate={self.max_rate} -- --id=@udp_queue create queue other-config:min-rate={self.udp_min_rate} '
            f'other-config:max-rate={self.max_rate}'
        ])
        self.logger.info("Initial QoS configured with minimum guarantees.")

    def monitor_traffic(self):
        """
        Monitor traffic utilization and adjust bandwidth dynamically.
        """
        while True:
            # Simulate traffic monitoring (replace with actual monitoring logic)
            tcp_utilization = self.get_queue_utilization(1)  # TCP queue
            udp_utilization = self.get_queue_utilization(2)  # UDP queue

            # Adjust bandwidth if UDP is idle
            if udp_utilization < 100000:  # Example threshold: 100 Kbps
                self.logger.info("UDP is idle, reallocating bandwidth to TCP.")
                self.adjust_bandwidth(tcp_share=1.0, udp_share=0.1)
            elif tcp_utilization > self.tcp_min_rate:
                self.logger.info("Reverting to guaranteed minimums.")
                self.adjust_bandwidth(tcp_share=0.1, udp_share=0.9)

            time.sleep(5)  # Check every 5 seconds

    def get_queue_utilization(self, queue_id):
        """
        Retrieve the utilization of a specific queue using OpenFlow statistics.
        :param queue_id: Queue ID to monitor (e.g., 1 for TCP, 2 for UDP).
        :return: Current bandwidth utilization (bps) for the given queue.
        """
        try:
            # Request queue statistics from all switches
            datapaths = self.datapaths.values()
            total_bytes = 0

            for datapath in datapaths:
                ofproto = datapath.ofproto
                parser = datapath.ofproto_parser

                # Send a request to the switch for queue statistics
                req = parser.OFPQueueStatsRequest(datapath, 0, ofproto.OFPP_ANY, queue_id)
                datapath.send_msg(req)

            # Wait briefly for replies
            hub.sleep(1)

            # Collect statistics from the replies
            for msg in self.queue_stats:
                for stat in msg.body:
                    if stat.queue_id == queue_id:
                        # Accumulate bytes transmitted by the queue
                        total_bytes += stat.tx_bytes

            # Convert total bytes to bits per second
            elapsed_time = 1  # Assuming a 1-second monitoring window
            bps = (total_bytes * 8) / elapsed_time
            return bps

        except Exception as e:
            self.logger.error(f"Error fetching queue utilization: {e}")
            return 0

    def adjust_bandwidth(self, tcp_share, udp_share):
        """
        Dynamically adjust bandwidth allocation.
        """
        tcp_rate = int(self.max_rate * tcp_share)
        udp_rate = int(self.max_rate * udp_share)

        self.ovs_vsctl.run_command([
            'set', 'port', self.bridge_name,
            f'qos=@newqos -- --id=@newqos create QoS type=linux-htb other-config:max-rate={self.max_rate} '
            f'queues:1=@tcp_queue queues:2=@udp_queue -- --id=@tcp_queue create queue other-config:min-rate={tcp_rate} '
            f'other-config:max-rate={self.max_rate} -- --id=@udp_queue create queue other-config:min-rate={udp_rate} '
            f'other-config:max-rate={self.max_rate}'
        ])
        self.logger.info(f"Bandwidth adjusted: TCP={tcp_rate}, UDP={udp_rate}")
