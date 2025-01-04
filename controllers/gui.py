import logging

from webob import Response
from webob.static import DirectoryApp
from ryu.app.wsgi import ControllerBase, route

from utils.constants import HTML_PATH, CSS_PATH, SCRIPT_PATH, GUI_BASE_URL

class Paths:
    
    INDEX = ''
    HTML_FILE = '/{filename}'
    CSS_FILE = '/css/{filename}'
    SCRIPT_FILE = '/scripts/{filename}'

for path in Paths.__dict__:
    if not path.startswith("__"):
        # if API_BASE_URL is not present in the path, add it
        if GUI_BASE_URL not in Paths.__dict__[path][::len(GUI_BASE_URL)]:
            setattr(Paths, path, GUI_BASE_URL + getattr(Paths, path))

logging.info(f"[GUIController] Loaded paths:")
for path in Paths.__dict__:
    if not path.startswith("__"):
        logging.info(f"\t- {path}: {getattr(Paths, path)}")

class GUIController(ControllerBase):

    def __init__(self, req, link, data, **config):
        super(GUIController, self).__init__(req, link, data, **config)
        logging.info("GUIController initialized")

        self.html_app = DirectoryApp(HTML_PATH)
        self.css_app = DirectoryApp(CSS_PATH)
        self.script_app = DirectoryApp(SCRIPT_PATH)
    
    @route('index', Paths.INDEX, methods=['GET'])
    def index(self, req, **kwargs):
        """REST endpoint to redirect to the index page."""
        logging.info("GUIController: index_endpoint")
        return Response(
            status="302",
            content_type='text/html',
            location=f'{GUI_BASE_URL}/index'
        )
    
    # =================== ONLY TO LOAD FILES INSIDE HTML =================== #
    
    @route('css', Paths.CSS_FILE, methods=['GET'], requirements={'filename': '.*'})
    def css(self, req, filename, **kwargs):
        """REST endpoint to get the css files."""
        req.path_info = f'/{filename}'
        return self.css_app(req)

    @route('scripts', Paths.SCRIPT_FILE, methods=['GET'], requirements={'filename': '.*'})
    def script(self, req, filename, **kwargs):
        """REST endpoint to get the script files."""
        req.path_info = f'/{filename}'
        return self.script_app(req)
    
    # =================== TO LOAD HTML PAGES =================== #
    
    @route('html', Paths.HTML_FILE, methods=['GET'])
    def html(self, req, **kwargs):
        """REST endpoint to get the html page."""
        if kwargs['filename']:
            req.path_info = kwargs['filename'] + ".html"
        return self.html_app(req)
