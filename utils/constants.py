from enum import Enum

# Mininet Constants
SWITCHES = 4
HOSTS = 4

# Ryu Controller Constants
CONTROLLER_INSTANCE_NAME = "dynamic_slicing_controller"
CONTROLLER_IP = "localhost"
CONTROLLER_PORT = 8080
OVSDB_ADDR = "tcp:127.0.0.1:6632"
NETWORK_MAX_RATE = 1000000000000  # In bps

# Base URL Constants
API_BASE_URL = "/api"
GUI_BASE_URL = "/gui"

# GUI Controller Constants
GUI_BASE_PATH = "./gui/"
HTML_PATH = GUI_BASE_PATH + "html"
CSS_PATH = GUI_BASE_PATH + "css"
SCRIPT_PATH = GUI_BASE_PATH + "script"

class FlowPriority(Enum):
    TABLE_MISS = 0
    FLOODING = 1
    DEFAULT = 2
