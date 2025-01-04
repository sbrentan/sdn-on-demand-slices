import json, logging

from webob import Response
from ryu.app.wsgi import ControllerBase, route

from utils.constants import CONTROLLER_INSTANCE_NAME, API_BASE_URL

class Paths:
    
    TOPOLOGY = '/topology'
    SLICES = '/slices'

for path in Paths.__dict__:
    if not path.startswith("__"):
        # if API_BASE_URL is not present in the path, add it
        if API_BASE_URL not in Paths.__dict__[path][::len(API_BASE_URL)]:
            setattr(Paths, path, API_BASE_URL + getattr(Paths, path))

logging.info(f"[APIController] Loaded paths:")
for path in Paths.__dict__:
    if not path.startswith("__"):
        logging.info(f"\t- {path}: {getattr(Paths, path)}")

class APIController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(APIController, self).__init__(req, link, data, **config)
        logging.info("APIController initialized")
        from ryu_app import DynamicSlicingController
        self.controller_instance: DynamicSlicingController = data[CONTROLLER_INSTANCE_NAME]

    ## ====================================== SLICES ====================================== ##

    @route('get_slices', Paths.SLICES, methods=['GET'])
    def get_slices(self, req, **kwargs):
        """REST endpoint to get the slices."""
        logging.info("APIController: get_slices_endpoint")
        slices_dict = [slice.to_dict() for slice in self.controller_instance.slices]
        return Response(text=json.dumps(self.controller_instance.link_to_slice_dict, default=str), content_type='application/json')

    @route('create_slice', Paths.SLICES, methods=['POST'])
    def create_slice(self, req, **kwargs):
        """REST endpoint to create a slice."""

    @route('update_slice', Paths.SLICES, methods=['PUT'])
    def update_slice(self, req, **kwargs):
        """REST endpoint to update a slice."""

    @route('delete_slice', Paths.SLICES, methods=['DELETE'])
    def delete_slice(self, req, **kwargs):
        """REST endpoint to delete a slice."""

    ## ====================================== TOPOLOGY ====================================== ##

    @route('get_topology', Paths.TOPOLOGY, methods=['GET'])
    def get_topology(self, req, **kwargs):
        """REST endpoint to get the topology."""
