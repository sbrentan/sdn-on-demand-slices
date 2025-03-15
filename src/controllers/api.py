import json, logging
from typing import Union

from webob import Response
from ryu.app.wsgi import ControllerBase, route
from ryu.topology.switches import Switch, Host

from common import Node, Slice, ApiPaths, Network
from managers.slices import SlicesManager
from utils import SliceUtils


class APIController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(APIController, self).__init__(req, link, data, **config)

        self.network = Network.get_instance()

        self.slices_manager: SlicesManager = data['slices_manager']

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
        # TODO: CHECK IF name already exists?
        # if [s for s in self.network.slices if s.id == slice_data["id"]]:
        #     logging.error(f"Error creating slice {slice_data['name']}: already exists")
        #     return self._json_response(status="409 Conflict")
        self.network.slices.append(Slice.from_dict(slice_data))

        # TODO: reset queues of affected switches

        return self._json_response(status="201 Created")

    @route('update_slice', ApiPaths.SLICE(), methods=['PUT'])
    def update_slice(self, req, slice_id, **kwargs):
        """REST endpoint to update a slice."""

        # TODO: reset queues if bandwidth/rules are updated

        try:
            slice_data = json.loads(req.body)
        except Exception as e:
            logging.error(f"Error updating slice: {e}")
            return self._json_response(status="400 Bad Request")
        slice_match = [s for s in self.network.slices if s.id == slice_id]
        if not slice_match:
            logging.error(f"Error updating slice {slice_id}: not found")
            return self._json_response(status="404 Not Found")
        slice_match[0].update_from_dict(slice_data)
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
