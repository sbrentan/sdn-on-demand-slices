import os
from time import sleep
from network import DynamicSlicingTopology


if __name__ == '__main__':
    print("Initiating controller...")
    os.system("ryu-manager --observe-links --verbose start_controller.py &")
    sleep(5)

    print("Initiating network...")
    topo = DynamicSlicingTopology()
    topo.start()
