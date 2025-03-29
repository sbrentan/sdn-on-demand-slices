import json, logging
from typing import Union

from webob import Response
from ryu.app.wsgi import ControllerBase, route

from common import Slice, ApiPaths, Network
from managers import SlicesManager, MonitoringManager
from utils import SliceUtils


class APIController(ControllerBase):

    def __init__(self, req, link, data, **config):
        super(APIController, self).__init__(req, link, data, **config)

        self.network = Network.get_instance()

        self.slices_manager: SlicesManager = data['slices_manager']
        self.monitoring_manager: MonitoringManager = data['monitoring_manager']

    def _json_response(self, data: Union[dict, list, None] = None, status: str = "200 OK") -> Response:
        if data:
            return Response(status=status, text=json.dumps(data, default=str), content_type='application/json')
        return Response(status=status)

    # ====================================== SLICES ====================================== #

    @route('get_slices', ApiPaths.SLICES(), methods=['GET'])
    def get_slices(self, req, **kwargs):
        """REST endpoint to get the slices."""
        slices_dict = []
        slice_links = {}
        link_to_slice_dict = SliceUtils.get_link_to_slice_dict(skip_active_slices=False)
        for connection in self.network.connections:
            if connection.link_id not in link_to_slice_dict:
                continue
            for slice in link_to_slice_dict[connection.link_id]:
                if slice.id not in slice_links:
                    slice_links[slice.id] = []
                slice_links[slice.id].append(connection.link_id)
        for slice in self.network.slices:
            slice_dict = slice.to_dict()
            slice_dict['links'] = slice_links[slice.id] if slice.id in slice_links else []
            slices_dict.append(slice_dict)
        return self._json_response(data=slices_dict)

    @route('get_slice', ApiPaths.SLICE(), methods=['GET'])
    def get_slice(self, req, slice_id, **kwargs):
        """REST endpoint to get the details of a specific slice."""
        slice = [s for s in self.network.slices if s.id == slice_id]
        if not slice:
            return self._json_response(status="404 Not Found")
        slice_dict = slice[0].to_dict()
        slice_links = []
        link_to_slice_dict = SliceUtils.get_link_to_slice_dict(skip_active_slices=False)
        for connection in self.network.connections:
            if slice[0] in link_to_slice_dict[connection.link_id]:
                slice_links.append(connection.link_id)
        slice_dict['links'] = slice_links
        return self._json_response(data=slice_dict)

    @route('create_slice', ApiPaths.SLICES(), methods=['POST'])
    def create_slice(self, req, **kwargs):
        """REST endpoint to create a slice."""
        try:
            slice_data = json.loads(req.body)
        except Exception as e:
            logging.error(f"Error creating slice: {e}")
            return self._json_response(status="400 Bad Request")
        new_slice = Slice.from_dict(slice_data)
        if new_slice.id in self.network.slices:
            logging.error(f"Error creating slice {slice_data['name']}: ID already exists")
            return self._json_response(status="409 Conflict")
        self.network.slices.append(new_slice)

        self.slices_manager.update_slice(new_slice)

        return self._json_response(status="201 Created", data=new_slice.to_dict())
    
    @route('reset_slices', ApiPaths.RESET_SLICES(), methods=['POST'])
    def reset_slices(self, req, **kwargs):
        """REST endpoint to reset all slices."""
        self.slices_manager.update_slice()
        return self._json_response(status="204 No Content")

    @route('update_slice', ApiPaths.SLICE(), methods=['PUT'])
    def update_slice(self, req, slice_id, **kwargs):
        """REST endpoint to update a slice."""

        try:
            slice_data = json.loads(req.body)
        except Exception as e:
            logging.error(f"Error updating slice: {e}")
            return self._json_response(status="400 Bad Request")
        slice_match = [s for s in self.network.slices if s.id == slice_id]
        if not slice_match:
            logging.error(f"Error updating slice {slice_id}: not found")
            return self._json_response(status="404 Not Found")
        
        affected_switches = self.slices_manager.update_slice(slice_match[0])
        slice_match[0].update_from_dict(slice_data)
        # TODO: when implementing the update of slice nodes, restore the following call:
        # self.slices_manager.update_slice(slice_match[0], switches_to_skip=affected_switches)
        # Calling two times `update_slice` to be sure to update and reset all queues of both previous and current affected switches

        logging.info(f"Updating slice {slice_id} with data: {slice_data}")
        logging.info(f"Updated slice: " + json.dumps(slice_match[0].to_dict(), indent=4))
        return self._json_response(status="200 OK", data=slice_match[0].to_dict())

    @route('delete_slice', ApiPaths.SLICE(), methods=['DELETE'])
    def delete_slice(self, req, slice_id, **kwargs):
        """REST endpoint to delete a slice."""
        slice_match = [s for s in self.network.slices if s.id == slice_id]
        if not slice_match:
            logging.error(f"Error deleting slice {slice_id}: not found")
            return self._json_response(status="404 Not Found")
        self.slices_manager.delete_slice(slice_match[0])
        return self._json_response(status="204 No Content")

    @route('activate_slice', ApiPaths.ACTIVATE_SLICE(), methods=['POST'])
    def activate_slice(self, req, slice_id, **kwargs):
        """REST endpoint to activate a slice."""
        slice_match = [s for s in self.network.slices if s.id == slice_id]
        if not slice_match:
            logging.error(f"Error activating slice {slice_id}: not found")
            return self._json_response(status="404 Not Found")
        slice = slice_match[0]
        self.slices_manager.enable_slice(slice)
        return self._json_response(status="200 OK")

    @route('deactivate_slice', ApiPaths.DEACTIVATE_SLICE(), methods=['POST'])
    def deactivate_slice(self, req, slice_id, **kwargs):
        """REST endpoint to deactivate a slice."""
        slice_match = [s for s in self.network.slices if s.id == slice_id]
        if not slice_match:
            logging.error(f"Error deactivating slice {slice_id}: not found")
            return self._json_response(status="404 Not Found")
        slice = slice_match[0]
        self.slices_manager.disable_slice(slice)
        return self._json_response(status="200 OK")
    

    # ====================================== HOSTS ====================================== #

    @route('update_host', ApiPaths.HOST(), methods=['PUT'])
    def update_host(self, req, host_id, **kwargs):
        """REST endpoint to update a host."""
        try:
            host_data = json.loads(req.body)
        except Exception as e:
            logging.error(f"Error updating host: {e}")
            return self._json_response(status="400 Bad Request")
        logging.info(f"Updating host {host_id} with data: {host_data}")
        if host_id not in self.network.hosts:
            logging.error(f"Error updating host {host_id}: not found")
            return self._json_response(status="404 Not Found")
        host = self.network.update_host_from_dict(host_id, host_data)
        return self._json_response(status="200 OK", data=host.to_dict())
    

    # ====================================== SWITCHES ====================================== #

    @route('update_switch', ApiPaths.SWITCH(), methods=['PUT'])
    def update_switch(self, req, switch_id, **kwargs):
        """REST endpoint to update a switch."""
        try:
            switch_data = json.loads(req.body)
        except Exception as e:
            logging.error(f"Error updating switch: {e}")
            return self._json_response(status="400 Bad Request")
        logging.info(f"Updating switch {switch_id} with data: {switch_data}")
        if switch_id not in self.network.switches:
            logging.error(f"Error updating switch {switch_id}: not found")
            return self._json_response(status="404 Not Found")
        switch = self.network.update_switch_from_dict(switch_id, switch_data)
        return self._json_response(status="200 OK", data=switch.to_dict())


    # ====================================== TOPOLOGY ====================================== #

    @route('get_nodes', ApiPaths.NODES(), methods=['GET'])
    def get_nodes(self, req, **kwargs):
        """REST endpoint to get the topology nodes."""
        nodes = []
        for node in self.network.nodes.values():
            node_dict = {"type": node.node_type}
            node_dict.update(node.to_dict())
            nodes.append(node_dict)
        return self._json_response(data=nodes)

    @route('get_switches', ApiPaths.SWITCHES(), methods=['GET'])
    def get_switches(self, req, **kwargs):
        """REST endpoint to get the topology switches."""
        switches = []
        for switch_id in self.network.switches.keys():
            switch_node = self.network.nodes[switch_id]
            switches.append(switch_node.to_dict())
        return self._json_response(data=switches)    
    
    @route('get_switch', ApiPaths.SWITCH(), methods=['GET'])
    def get_switch(self, req, switch_id, **kwargs):
        """REST endpoint to get the details of a specific switch."""
        switch_node = self.network.nodes[switch_id]
        return self._json_response(data=switch_node.to_dict())
    
    @route('get_hosts', ApiPaths.HOSTS(), methods=['GET'])
    def get_hosts(self, req, **kwargs):
        """REST endpoint to get the topology hosts."""
        hosts = []
        for host_id in self.network.hosts.keys():
            host_node = self.network.nodes[host_id]
            hosts.append(host_node.to_dict())
        return self._json_response(data=hosts)
    
    @route('get_host', ApiPaths.HOST(), methods=['GET'])
    def get_host(self, req, host_id, **kwargs):
        """REST endpoint to get the details of a specific host."""
        host_node = self.network.nodes[host_id]
        return self._json_response(data=host_node.to_dict())

    @route('get_links', ApiPaths.LINKS(), methods=['GET'])
    def get_links(self, req, **kwargs):
        """REST endpoint to get the topology links."""
        links = []
        for connection in self.network.connections:
            links.append({
                "id": connection.link_id,
                "source": connection.src[1].node_id,
                "target": connection.dst[1].node_id
            })
        return self._json_response(data=links)

    @route('get_link', ApiPaths.LINK(), methods=['GET'])
    def get_link(self, req, link_id, **kwargs):
        """REST endpoint to get the details of a specific link."""
        link = [c for c in self.network.connections if c.link_id == link_id]
        if not link:
            return self._json_response(status="404 Not Found")
        link = link[0]
        link_to_slice_dict = SliceUtils.get_link_to_slice_dict(skip_active_slices=False)
        return self._json_response(data={
            "id": link_id,
            "source": link.src[1].name,
            "target": link.dst[1].name,
            "slices": [s.to_dict() for s in link_to_slice_dict[link_id]]
        })


    # ====================================== MONITORING ====================================== #

    @route('send_packet', ApiPaths.SEND_PACKET(), methods=['POST'])
    def send_packet(self, req, **kwargs):
        """REST endpoint to send a packet."""
        try:
            packet_data = json.loads(req.body)
        except Exception as e:
            logging.error(f"Error sending packet: {e}")
            return self._json_response(status="400 Bad Request")
        network = Network.get_instance()
        src_port = packet_data.get("src_port", None)
        if src_port:
            src_port = int(src_port)
        dst_port = int(packet_data.get("dst_port"))
        packet_info = {
            "protocol": packet_data.get("protocol"),
            "dst_port": dst_port,
            "src_port": src_port,
            "src_mac": network.hosts[packet_data.get("source")].mac,
            "dst_mac": network.hosts[packet_data.get("dest")].mac,
        }
        packet_id = self.monitoring_manager.send_packet(packet_info)
        logging.info(f"Sending packet: {packet_info} with id {packet_id}")
        return self._json_response(status="201 Created", data={"packet_id": packet_id})
    
    @route('get_packet', ApiPaths.PACKET(), methods=['GET'])
    def get_packet(self, req, **kwargs):
        """REST endpoint to get the details of a specific packet."""
        if self.monitoring_manager.active_packet:
            try:
                packet = self.monitoring_manager.get_packet()
                packet.update({"status": "available"})
            except ValueError as e:
                logging.error(f"Error getting packet: {e}")
                return self._json_response(status="404 Not Found")
        else:
            packet = {"status": "no_packets"}
        return self._json_response(data=packet)
    
    @route('get_packet_result', ApiPaths.PACKET_RESULT(), methods=['GET'])
    def get_packet_result(self, req, packet_id, **kwargs):
        """REST endpoint to get the details of a specific packet."""
        try:
            if self.monitoring_manager.packet_result_is_available(packet_id):
                packet_steps = self.monitoring_manager.get_packet_result(packet_id)
                packet = {"packet_id": packet_id, "steps": packet_steps, "status": "completed"}
            else:
                packet = {"status": "pending"}
        except ValueError as e:
            logging.error(f"Error getting packet: {e}")
            return self._json_response(status="404 Not Found")
        return self._json_response(data=packet)
     
    @route('save_packet_result', ApiPaths.PACKET_RESULT(), methods=['POST'])
    def save_packet_result(self, req, packet_id, **kwargs):
        """REST endpoint to save the result of a packet."""
        import traceback
        try:
            packet_result = json.loads(req.body)
        except Exception as e:
            logging.error(f"Error saving packet result: {e}")
            logging.error(traceback.format_exc())
            return self._json_response(status="400 Bad Request")
        try:
            self.monitoring_manager.save_packet_result(packet_id, packet_result)
        except ValueError as e:
            logging.error(f"Error saving packet result: {e}")
            return self._json_response(status="404 Not Found")
        return self._json_response(status="201 Created")
    
    @route('new_recording', ApiPaths.RECORDINGS(), methods=['POST'])
    def new_recording(self, req, **kwargs):
        """REST endpoint to create a new recording."""
        recording_id = self.monitoring_manager.new_recording()
        return self._json_response(status="201 Created", data={"recording_id": recording_id})
    
    @route('get_recording', ApiPaths.RECORDING(), methods=['GET'])
    def get_recording(self, req, recording_id, **kwargs):
        """REST endpoint to get the details of a specific recording."""
        try:
            recording_id = int(recording_id)
        except Exception as e:
            logging.error(f"Error getting recording: {e}")
            return self._json_response(status="400 Bad Request")
        try:
            recording = self.monitoring_manager.get_recording(recording_id)
        except ValueError as e:
            logging.error(f"Error getting recording: {e}")
            return self._json_response(status="404 Not Found")
        
        data = []
        for node, packet in recording:
            data.append(node.to_dict())
            # for protocol in packet.protocols:
            #     logging.info(f"Protocol: {protocol}")
                
        return self._json_response(data=data)
