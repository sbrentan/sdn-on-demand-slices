import logging
from typing import List

from common import Network, Connection, Slice, Protocol


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
        link_to_slice_dict = {}
        for slice in self.network.slices:
            if not slice.active:
                continue
            for connection in self.network.connections:
                connection_id = Connection.get_link_id(connection)
                if connection_id not in link_to_slice_dict:
                    link_to_slice_dict[connection_id] = []
                if connection.is_host_connection:
                    if connection.src[1].ref_id in slice.hosts:
                        if slice.name not in [s.name for s in link_to_slice_dict[connection_id]]:
                            link_to_slice_dict[connection_id].append(slice)
                elif connection.src[1].ref_id in slice.switches and connection.dst[1].ref_id in slice.switches:
                    if slice.name not in [s.name for s in link_to_slice_dict[connection_id]]:
                        link_to_slice_dict[connection_id].append(slice)
        logging.info("link_to_slice dicts: " + str(link_to_slice_dict))
        self.network.link_to_slice_dict = link_to_slice_dict
    
    # TODO: implement logic for initializing the slices (e.g., default slice templates or from a file)
    # TODO: move logic for creating, updating, deleting slices from API controller to here
    # TODO: implement logic for enabling and disabling slices
