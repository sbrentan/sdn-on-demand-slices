import logging
import json

from webob import Response
from ryu.app.wsgi import ControllerBase, route

from utils.constants import CONTROLLER_INSTANCE_NAME, NETWORK_BASE_URL

class APIController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(APIController, self).__init__(req, link, data, **config)
        logging.info("APIController initialized")
        from controller import DynamicSlicingController # avoid circular import
        self.controller_instance: DynamicSlicingController = data[CONTROLLER_INSTANCE_NAME]

    @route('network', NETWORK_BASE_URL + '/init', methods=['POST'])
    def init_network_endpoint(self, req, **kwargs):
        """REST endpoint to initialize the network."""
        logging.info("APIController: init_network_endpoint")
        self.controller_instance.init_network()
        return Response(text=json.dumps(self.controller_instance.link_to_slice_dict, default=str), content_type='application/json')
