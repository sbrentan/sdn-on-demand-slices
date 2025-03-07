import logging

from common import Network, Connection, Slice, Protocol, NodeType
from utils import QueueUtils, PacketUtils, SliceUtils


S = ["s1", "s2", "s3", "s4"]
H = ["h00:00:00:00:00:01", "h00:00:00:00:00:02", "h00:00:00:00:00:03", "h00:00:00:00:00:04"]

class SlicesManager:

    network: Network

    def __init__(self, network: Network):
        self.network = network
    
        # TODO: read from file ???
        self.network.slices = [
            Slice(name="slice1", switches=[S[0], S[1], S[3]], hosts=[H[0], H[2]], min_rate=9000000, max_rate=9000000, rules={
                "allowed_services": {
                    "10.0.0.3": [9999, 9998],
                },
                "allowed_protocols": [Protocol.UDP.value],
            }),
            # Slice(name="slice2", switches=["s1", "s3", "s4"], hosts=["h2", "h4"], bandwidth=1000, rules={
            #     "allowed_protocols": [Protocol.TCP.value],
            # }),
            Slice(name="slice3", switches=[S[0], S[2], S[3]], hosts=[H[0], H[1], H[2], H[3]], min_rate=1000, max_rate=1000, rules={
                "allowed_protocols": [Protocol.ICMP.value],
            }),
        ]
        logging.info("slices: " + str(self.network.slices))

        self.network.add_update_event(self.init_slices)
        
    def init_slices(self):
        if not self.network:
            logging.error("[INIT SLICES] Network not initialized yet...")
            return
        logging.info("Initializing slices...")
        link_to_slice_dict = SliceUtils.get_link_to_slice_dict()
        logging.info("link_to_slice dicts: " + str(link_to_slice_dict))
        self.network.link_to_slice_dict = link_to_slice_dict

    def enable_slice(self, slice: Slice):
        slice.active = True
        self._reset_switches_for_slice(slice)

    def disable_slice(self, slice: Slice):
        slice.active = False
        self._reset_switches_for_slice(slice)

    def _reset_switches_for_slice(self, slice: Slice):
        link_to_slice_dict = SliceUtils.get_link_to_slice_dict(skip_active_slices=False)
        affected_switches = {}
        for connection in self.network.connections:
            connection_id = Connection.get_link_id(connection)
            if slice.name in [s.name for s in link_to_slice_dict[connection_id]]:
                if connection.src[1].node_type == NodeType.SWITCH:
                    affected_switches[connection.src[1].node_id] = connection.src[1].node_ref
                if connection.dst[1].node_type == NodeType.SWITCH:
                    affected_switches[connection.dst[1].node_id] = connection.dst[1].node_ref
        logging.info(f"Affected switches: {affected_switches}")
        self.init_slices()
        for switch in affected_switches.values():
            QueueUtils.delete_queues(switch.dp.id)
            PacketUtils.delete_flows(switch)

    # TODO: implement logic for initializing the slices (e.g., default slice templates or from a file)
    # TODO: move logic for creating, updating, deleting slices from API controller to here
    # TODO: implement logic for enabling and disabling slices
