import json, logging

from webob import Response
from ryu.app.wsgi import ControllerBase, route

from utils.topology import TopologyUtils, Switch, Host, Node
from utils.constants import CONTROLLER_INSTANCE_NAME
from controllers.utils.paths import ApiPaths


class APIController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(APIController, self).__init__(req, link, data, **config)

        from ryu_app import DynamicSlicingController
        self.controller_instance: DynamicSlicingController = data[CONTROLLER_INSTANCE_NAME]

    def _json_response(self, data: dict) -> Response:
        return Response(text=json.dumps(data, default=str), content_type='application/json')

    ## ====================================== SLICES ====================================== ##

    @route('get_slices', ApiPaths.SLICES(), methods=['GET'])
    def get_slices(self, req, **kwargs):
        """REST endpoint to get the slices."""
        slices_dict = []
        slice_links = {}
        for connection in TopologyUtils.connections:
            for slice in self.controller_instance.link_to_slice_dict[connection.link_id]:
                if slice.name not in slice_links:
                    slice_links[slice.name] = []
                slice_links[slice.name].append(connection.link_id)
        for slice in self.controller_instance.slices:
            slice_dict = slice.to_dict()
            slice_dict['links'] = slice_links[slice.name]
            slices_dict.append(slice_dict)
        return self._json_response(slices_dict)

    @route('create_slice', ApiPaths.SLICES(), methods=['POST'])
    def create_slice(self, req, **kwargs):
        """REST endpoint to create a slice."""

    @route('update_slice', ApiPaths.SLICES(), methods=['PUT'])
    def update_slice(self, req, **kwargs):
        """REST endpoint to update a slice."""

    @route('delete_slice', ApiPaths.SLICES(), methods=['DELETE'])
    def delete_slice(self, req, **kwargs):
        """REST endpoint to delete a slice."""

    ## ====================================== TOPOLOGY ====================================== ##

    @route('get_nodes', ApiPaths.NODES(), methods=['GET'])
    def get_nodes(self, req, **kwargs):
        """REST endpoint to get the topology nodes."""
        nodes = []
        hosts = TopologyUtils.get_all_hosts(self.controller_instance)
        for node_id, node in TopologyUtils.nodes.items():
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
        return self._json_response(nodes)

    @route('get_switches', ApiPaths.SWITCHES(), methods=['GET'])
    def get_switches(self, req, **kwargs):
        """REST endpoint to get the topology switches."""
        switches = []
        for switch_id, switch in TopologyUtils.switches.items():
            switches.append({
                "id": switch_id,
                "dpid": switch.dp.id
            })
        return self._json_response(switches)    
    
    @route('get_switch', ApiPaths.SWITCH(), methods=['GET'])
    def get_switch(self, req, switch_id, **kwargs):
        """REST endpoint to get the details of a specific switch."""
        switch = TopologyUtils.switches[switch_id]
        return self._json_response({
            "id": switch_id,
            "dpid": switch.dp.id
        })
    
    @route('get_hosts', ApiPaths.HOSTS(), methods=['GET'])
    def get_hosts(self, req, **kwargs):
        """REST endpoint to get the topology hosts."""
        hosts = []
        for host_id, host in TopologyUtils.hosts.items():
            hosts.append({
                "id": host_id,
                "ip": host.ipv4,
                "mac": host.mac
            })
        return self._json_response(hosts)
    
    @route('get_host', ApiPaths.HOST(), methods=['GET'])
    def get_host(self, req, host_id, **kwargs):
        """REST endpoint to get the details of a specific host."""
        host = TopologyUtils.hosts[host_id]
        return self._json_response({
            "id": host_id,
            "ip": host.ipv4,
            "mac": host.mac
        })

    @route('get_links', ApiPaths.LINKS(), methods=['GET'])
    def get_links(self, req, **kwargs):
        """REST endpoint to get the topology links."""
        links = []
        for connection in TopologyUtils.connections:
            links.append({
                "id": connection.link_id,
                "source": connection.src[1].node_id,
                "target": connection.dst[1].node_id
            })
        return self._json_response(links)
