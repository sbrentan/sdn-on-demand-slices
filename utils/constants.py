from enum import Enum

# Mininet Constants
SWITCHES = 4
HOSTS = 4

# Ryu Controller Constants
CONTROLLER_INSTANCE_NAME = "dynamic_slicing_controller"
NETWORK_BASE_URL = "/network"
CONTROLLER_IP = "localhost"
CONTROLLER_PORT = 8080
OVSDB_ADDR = "tcp:127.0.0.1:6632"
NETWORK_MAX_RATE = 1000000000000  # In bps

class FlowPriority(Enum):
    TABLE_MISS = 0
    FLOODING = 1
    DEFAULT = 2
