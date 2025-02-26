import logging, os, httpx, json

from jinja2 import Environment, FileSystemLoader
from webob import Response
from webob.static import DirectoryApp
from ryu.app.wsgi import ControllerBase, route

from controllers.utils.dict_object import DictObject
from controllers.utils.paths import ApiPaths, GuiPaths
from utils.constants import GUI_BASE_URL, CONTROLLER_IP, CONTROLLER_PORT, STATIC_DIR, TEMPLATE_DIR

STATIC_DIR =  os.path.join(os.path.dirname(os.path.dirname(__file__)), STATIC_DIR)
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), TEMPLATE_DIR)


class GUIController(ControllerBase):

    def __init__(self, req, link, data, **config):
        super(GUIController, self).__init__(req, link, data, **config)
    
        self.static_app = DirectoryApp(STATIC_DIR)
        self.jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

    def get_data(self, endpoint, method="GET", data=None):
        url = f"http://{CONTROLLER_IP}:{CONTROLLER_PORT}{endpoint}"

        try:
            response = httpx.request(
                method=method,
                url=url,
                data=json.dumps(data),  # type: ignore
            )

            response_status = response.status_code
            response_data = json.loads(response.text)

            return response_status, response_data
        
        except Exception as e:
            logging.error(f"Error while trying to fetch data from {url}: {e}")
            return 500, None

    def render_template(self, template_name, context={}):
        """Renders a Jinja2 template with the given context."""
        template_name = f"{template_name}.html"
        template = self.jinja_env.get_template(template_name)
        context.update({
            "base_url": GUI_BASE_URL,
            "Paths": GuiPaths,
        })
        render = template.render(context)
        return Response(body=render, content_type="text/html")
    
    @route('default', '/', methods=['GET'])
    def default(self, req, **kwargs):
        """Default redirect to the GUI if no path (/gui or /api) is provided."""
        return Response(status="302", location=GuiPaths.INDEX())
    
    @route('static', GuiPaths.STATIC(), methods=['GET'], requirements={'filename': '.*'})
    def static(self, req, filename, **kwargs):
        req.path_info = f'/{filename}'
        return self.static_app(req)
    
    @route('gui', GuiPaths.INDEX(), methods=['GET'])
    def index(self, req, **kwargs):
        """REST endpoint to serve the Index page."""
        return self.render_template("index")
    
    @route('switch_details', GuiPaths.SWITCH_DETAILS(), methods=['GET'])
    def switch_details(self, req, switch_id, **kwargs):
        """REST endpoint to serve the details of a specific switch."""

        status, switch = self.get_data(ApiPaths.SWITCH(switch_id))
        
        if status != 200:
            return Response(status=status, body=f"Error while trying to fetch switch data: {switch}")
        
        # return Response(status=200, body=f"Switch details: {switch}")

        context = {
            "switch": DictObject(**switch)
        }

        return self.render_template(f"details/switch", context)
    
    @route('host_details', GuiPaths.HOST_DETAILS(), methods=['GET'])
    def host_details(self, req, **kwargs):
        """REST endpoint to serve the details of a specific host."""

        context = {
            "host": {
                "name": 'Host 1',
            }
        }

        return self.render_template(f"details/host", context)
    
    @route('slice_details', GuiPaths.SLICE_DETAILS(), methods=['GET'])
    def slice_details(self, req, **kwargs):
        """REST endpoint to serve the details of a specific slice."""

        context = {
            "slice": DictObject({
                "name": 'Slice 1',
            })
        }

        return self.render_template(f"details/slice", context)
