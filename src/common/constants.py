from enum import Enum

# Mininet Constants
DEBUG = False

# Ryu Controller Constants
CONTROLLER_IP = "localhost"
CONTROLLER_PORT = 8080
OVSDB_ADDR = "tcp:127.0.0.1:6632"
OVSDB_TIMEOUT = 10  # In seconds
NETWORK_MAX_RATE = 10000000000  # In bps (=10 Gbps)

# Base URL Constants
API_BASE_URL = "/api"
GUI_BASE_URL = "/gui"

# GUI Controller Constants
STATIC_DIR = "gui/static"
TEMPLATE_DIR = "gui/templates"

class FlowPriority(Enum):
    TABLE_MISS = 0
    FLOODING = 1
    DEFAULT = 2
