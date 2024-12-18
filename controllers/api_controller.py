from ryu.app.wsgi import ControllerBase, route


CONTROLLER_INSTANCE_NAME = 'dynamic_slicing_controller_api'
BASE_URL = '/network'

class APIController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(APIController, self).__init__(req, link, data, **config)
        self.controller_instance = data[CONTROLLER_INSTANCE_NAME]

    @route('network', BASE_URL + '/init', methods=['POST'])
    def init_network_endpoint(self, req, **kwargs):
        """REST endpoint to initialize the network."""
        controller = self.controller_instance
        controller.init_network()
        return self._response("Network initialized successfully.")

    def _response(self, message, status=200):
        """Utility to create a JSON response."""
        from webob import Response
        import json
        return Response(content_type='application/json', body=json.dumps({'message': message}), status=str(status))
