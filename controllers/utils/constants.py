from enum import Enum

CONTROLLER_INSTANCE_NAME = "dynamic_slicing_controller"
NETWORK_BASE_URL = "/network"
CONTROLLER_IP = "localhost"
CONTROLLER_PORT = 8080
OVSDB_ADDR = "tcp:127.0.0.1:6632"

class FlowPriority(Enum):
    TABLE_MISS = 0
    FLOODING = 1
    DEFAULT = 2
