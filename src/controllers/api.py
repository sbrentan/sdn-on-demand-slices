import json, logging
from typing import Union

from webob import Response
from ryu.app.wsgi import ControllerBase, route
from ryu.topology.switches import Switch, Host

from common import Node, Slice, ApiPaths, Network


class APIController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(APIController, self).__init__(req, link, data, **config)

        self.network = Network.get_instance()

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
        for connection in self.network.connections:
            for slice in self.network.link_to_slice_dict[connection.link_id]:
                if slice.name not in slice_links:
                    slice_links[slice.name] = []
                slice_links[slice.name].append(connection.link_id)
        for slice in self.network.slices:
            slice_dict = slice.to_dict()
            slice_dict['links'] = slice_links[slice.name] if slice.name in slice_links else []
            slices_dict.append(slice_dict)
        return self._json_response(data=slices_dict)

    @route('get_slice', ApiPaths.SLICE(), methods=['GET'])
    def get_slice(self, req, slice_id, **kwargs):
        """REST endpoint to get the details of a specific slice."""
        slice = [s for s in self.network.slices if s.name == slice_id]
        if not slice:
            return self._json_response(status="404 Not Found")
        slice_dict = slice[0].to_dict()
        slice_links = []
        for connection in self.network.connections:
            if slice[0] in self.network.link_to_slice_dict[connection.link_id]:
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
        if [s for s in self.network.slices if s.name == slice_data["name"]]:
            logging.error(f"Error creating slice {slice_data['name']}: already exists")
            return self._json_response(status="409 Conflict")
        self.network.slices.append(Slice.from_dict(slice_data))
        return self._json_response(status="201 Created")

    @route('update_slice', ApiPaths.SLICES(), methods=['PUT'])
    def update_slice(self, req, **kwargs):
        """REST endpoint to update a slice."""
        try:
            slice_data = json.loads(req.body)
            slice_id = slice_data["id"]
        except Exception as e:
            logging.error(f"Error updating slice: {e}")
            return self._json_response(status="400 Bad Request")
        slice_match = [s for s in self.network.slices if s.name == slice_id]
        if not slice_match:
            logging.error(f"Error updating slice {slice_data['name']}: not found")
            return self._json_response(status="404 Not Found")
        slice_match[0].update_from_dict(slice_data)
        return self._json_response(status="200 OK", data=slice_match[0].to_dict())

    @route('delete_slice', ApiPaths.SLICES(), methods=['DELETE'])
    def delete_slice(self, req, **kwargs):
        """REST endpoint to delete a slice."""
        try:
            slice_id = json.loads(req.body)["id"]
        except Exception as e:
            logging.error(f"Error deleting slice: {e}")
            return self._json_response(status="400 Bad Request")
        slice_match = [s for s in self.network.slices if s.name == slice_id]
        if not slice_match:
            logging.error(f"Error deleting slice {slice_id}: not found")
            return self._json_response(status="404 Not Found")
        self.network.slices.remove(slice_match[0])
        return self._json_response(status="204 No Content")

    @route('activate_slice', ApiPaths.ACTIVATE_SLICE(), methods=['GET'])
    def activate_slice(self, req, slice_id, **kwargs):
        """REST endpoint to activate a slice."""
        slice_match = [s for s in self.network.slices if s.name == slice_id]
        if not slice_match:
            logging.error(f"Error activating slice {slice_id}: not found")
            return self._json_response(status="404 Not Found")
        slice = slice_match[0]
        slice.activate() # TODO: change?
        # TODO: implement slice activation (enable QoS queues on switches)
        return self._json_response(status="200 OK")

    @route('deactivate_slice', ApiPaths.DEACTIVATE_SLICE(), methods=['GET'])
    def deactivate_slice(self, req, slice_id, **kwargs):
        """REST endpoint to deactivate a slice."""
        slice_match = [s for s in self.network.slices if s.name == slice_id]
        if not slice_match:
            logging.error(f"Error deactivating slice {slice_id}: not found")
            return self._json_response(status="404 Not Found")
        slice = slice_match[0]
        slice.deactivate() # TODO: change?
        # TODO: implement slice deactivation (disable QoS queues on switches)
        return self._json_response(status="200 OK")


    # ====================================== TOPOLOGY ====================================== #

    @route('get_nodes', ApiPaths.NODES(), methods=['GET'])
    def get_nodes(self, req, **kwargs):
        """REST endpoint to get the topology nodes."""
        nodes = []
        hosts = self.network.hosts
        for node_id, node in self.network.nodes.items():
            node_dict = {
                "id": node_id,
                "type": node.node_type,
            }
            if isinstance(node.node_ref, Switch):
                node_dict["dpid"] = node.node_ref.dp.id
            elif isinstance(node.node_ref, Host):
                host = hosts[Node.get_host_id(node.node_ref.mac)]
                node_dict["ip"] = host.ipv4
                node_dict["mac"] = host.mac
            nodes.append(node_dict)
        return self._json_response(data=nodes)

    @route('get_switches', ApiPaths.SWITCHES(), methods=['GET'])
    def get_switches(self, req, **kwargs):
        """REST endpoint to get the topology switches."""
        switches = []
        for switch_id, switch in self.network.switches.items():
            switches.append({
                "id": switch_id,
                "dpid": switch.dp.id
            })
        return self._json_response(data=switches)    
    
    @route('get_switch', ApiPaths.SWITCH(), methods=['GET'])
    def get_switch(self, req, switch_id, **kwargs):
        """REST endpoint to get the details of a specific switch."""
        switch = self.network.switches[switch_id]
        return self._json_response(data={
            "id": switch_id,
            "dpid": switch.dp.id
        })
    
    @route('get_hosts', ApiPaths.HOSTS(), methods=['GET'])
    def get_hosts(self, req, **kwargs):
        """REST endpoint to get the topology hosts."""
        hosts = []
        for host_id, host in self.network.hosts.items():
            hosts.append({
                "id": host_id,
                "ip": host.ipv4,
                "mac": host.mac
            })
        return self._json_response(data=hosts)
    
    @route('get_host', ApiPaths.HOST(), methods=['GET'])
    def get_host(self, req, host_id, **kwargs):
        """REST endpoint to get the details of a specific host."""
        host = self.network.hosts[host_id]
        return self._json_response(data={
            "id": host_id,
            "ip": host.ipv4,
            "mac": host.mac
        })

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
