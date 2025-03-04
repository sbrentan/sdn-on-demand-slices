from utils.slice import Slice
from typing import List

import logging

class SliceHandler:

    slices: List[Slice] = []

    def __init__(self, controller_instance):  
        from ryu_app import DynamicSlicingController      
        self.controller_instance: DynamicSlicingController = controller_instance
    
    # TODO: implement logic for initilizing the slices (e.g., default slice templates or from a file)
    # TODO: move logic for creating, updating, deleting slices from API controller to here
    # TODO: implement logic for enabling and disabling slices
