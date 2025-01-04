import logging

from webob.static import DirectoryApp

from ryu.app.wsgi import ControllerBase, route

from utils.constants import HTML_PATH, CSS_PATH, SCRIPT_PATH, GUI_BASE_URL

class Paths:
    
    INDEX = '/'
    CSS_FILE = '/css/{filename:.*}'
    SCRIPT_FILE = '/script/{filename:.*}'

for path in Paths.__dict__:
    if not path.startswith("__"):
        # if API_BASE_URL is not present in the path, add it
        if GUI_BASE_URL not in Paths.__dict__[path][::len(GUI_BASE_URL)]:
            setattr(Paths, path, GUI_BASE_URL + getattr(Paths, path))

class GUIController(ControllerBase):

    def __init__(self, req, link, data, **config):
        super(GUIController, self).__init__(req, link, data, **config)
        logging.info("GUIController initialized")

        self.html_app = DirectoryApp(HTML_PATH)
        self.css_app = DirectoryApp(CSS_PATH)
        self.script_app = DirectoryApp(SCRIPT_PATH)

    @route('index', '/', methods=['GET'])
    def index(self, req, **kwargs):
        """REST endpoint to get the index."""
        logging.info("GUIController: index_endpoint")
        return self.html_app(req)
    
    # =================== ONLY TO LOAD FILES INSIDE HTML =================== #
    
    @route('css', Paths.CSS_FILE, methods=['GET'])
    def css(self, req, filename, **kwargs):
        """REST endpoint to get the css files. Needed for the GUI app."""
        logging.info("GUIController: css_endpoint")
        req.path_info = f'/{filename}'
        return self.css_app(req)
    
    @route('script', Paths.SCRIPT_FILE, methods=['GET'])
    def script(self, req, filename, **kwargs):
        """REST endpoint to get the script files. Needed for the GUI app."""
        logging.info("GUIController: script_endpoint")
        req.path_info = f'/{filename}'
        return self.script_app(req)
    
    # =================== TO LOAD HTML PAGES =================== #
    
    @route('html', Paths.INDEX, methods=['GET'])
    def html(self, req, filename, **kwargs):
        """REST endpoint to get the html page."""
        logging.info("GUIController: html_endpoint")
        req.path_info = f'/{filename}'
        return self.html_app(req)
