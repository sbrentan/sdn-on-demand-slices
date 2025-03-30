import json
import logging
from typing import Optional, List

from common import Network, Connection, Slice, NodeType
from utils import QueueUtils, PacketUtils, SliceUtils


class SlicesManager:

    network: Network

    def __init__(self, network: Network, slices_dict: dict = None):
        self.network = network
    
        self.network.slices = [Slice.from_dict(s) for s in slices_dict.get("slices", [])] if slices_dict else []
        logging.info("Loaded slices from file: " + str(self.network.slices))

        self.network.add_update_event(self.init_slices)
        
    def init_slices(self):
        if not self.network:
            logging.error("[INIT SLICES] Network not initialized yet...")
            return
        logging.info("Initializing slices...")
        link_to_slice_dict = SliceUtils.get_link_to_slice_dict()
        logging.info("link_to_slice dicts: " + str(link_to_slice_dict))
        self.network.link_to_slice_dict = link_to_slice_dict

        # print all slices to dict
        slices_to_print = {s.id: s.to_dict() for s in self.network.slices}
        logging.info(f"Slices: {json.dumps(slices_to_print, indent=4)}")

    def enable_slice(self, slice: Slice):
        slice.active = True
        affected_switches = self._reset_switches_for_slice(slice)
        self.init_slices()
        QueueUtils.init_queues(affected_switches)

    def disable_slice(self, slice: Slice):
        slice.active = False
        affected_switches = self._reset_switches_for_slice(slice)
        self.init_slices()
        QueueUtils.init_queues(affected_switches)

    def delete_slice(self, slice: Slice):
        affected_switches = self._reset_switches_for_slice(slice)
        self.network.slices.remove(slice)
        self.init_slices()
        QueueUtils.init_queues(affected_switches)

    def update_slice(self, slice: Optional[Slice] = None, switches_to_skip: List[str] = None) -> List[str]:
        """
        Update the slice and reset the switches for the slice.
        Skip the switches that are in the switches_to_skip list.
        :param slice: Slice to update
        :param switches_to_skip: List of switches to skip
        :return: List of affected switches
        """
        affected_switches = self._reset_switches_for_slice(slice, switches_to_skip=switches_to_skip)
        self.init_slices()
        QueueUtils.init_queues(affected_switches)
        return affected_switches

    def _reset_switches_for_slice(self, slice: Optional[Slice] = None, switches_to_skip: List[str] = None) -> List[str]:
        if not switches_to_skip:
            switches_to_skip = []
        link_to_slice_dict = SliceUtils.get_link_to_slice_dict(skip_active_slices=False)
        affected_switches = {}
        for connection in self.network.connections:
            connection_id = Connection.get_link_id(connection)
            if not slice or slice.id in [s.id for s in link_to_slice_dict[connection_id]]:
                if connection.src[1].node_type == NodeType.SWITCH:
                    affected_switches[connection.src[1].node_id] = connection.src[1].node_ref
                if connection.dst[1].node_type == NodeType.SWITCH:
                    affected_switches[connection.dst[1].node_id] = connection.dst[1].node_ref
        # remove switches that are in the switches_to_skip list
        if switches_to_skip:
            affected_switches = {k: v for k, v in affected_switches.items() if k not in switches_to_skip}
        logging.info(f"Affected switches: {affected_switches}")
        for switch in affected_switches.values():
            QueueUtils.delete_queues(switch.dp.id)
            PacketUtils.delete_flows(switch)
        return affected_switches.keys()
