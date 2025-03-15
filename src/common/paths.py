import re
import logging

from .constants import API_BASE_URL, GUI_BASE_URL

class Paths:

    def __init_subclass__(cls, BASE_URL='', **kwargs):
        super().__init_subclass__()

        for path in cls.__dict__:
            if not path.startswith("_"):
                # if GUI_BASE_URL is not present in the path, add it
                if BASE_URL not in cls.__dict__[path][::len(BASE_URL)]:
                    def attr_fun(*args, local_path=getattr(cls, path)):
                        if args:
                            var_names = re.findall(r'\{(\w+)\}', local_path)
                            if len(var_names) != len(args):
                                raise ValueError(f"Invalid number of arguments for path {path}")
                            path_args = dict(zip(var_names, args))
                            return (BASE_URL + local_path).format(**path_args)
                        return BASE_URL + local_path
                    setattr(cls, path, attr_fun)

        logging.info(f"[{cls.__name__}] Loaded paths:")
        for path in cls.__dict__:
            if not path.startswith("__"):
                logging.info(f"\t- {path}: {getattr(cls, path)()}")


class ApiPaths(Paths, BASE_URL=API_BASE_URL):
    SLICES = '/slices'
    SLICE = '/slices/{slice_id}'
    ACTIVATE_SLICE = '/slices/{slice_id}/activate'
    DEACTIVATE_SLICE = '/slices/{slice_id}/deactivate'
    TOPOLOGY = '/topology'
    NODES = '/topology/nodes'
    SWITCHES = '/topology/switches'
    SWITCH = '/topology/switches/{switch_id}'
    HOSTS = '/topology/hosts'
    HOST = '/topology/hosts/{host_id}'
    LINKS = '/topology/links'
    LINK = '/topology/links/{link_id}'


class GuiPaths(Paths, BASE_URL=GUI_BASE_URL):
    INDEX = ''
    STATIC = '/static/{filename}'
    HOST = '/host/{host_id}'
    SWITCH = '/switch/{switch_id}'
    SLICE = '/slice/{slice_id}'
    SLICES = '/slices'
    SWITCH_DETAILS = '/menu/details/switch/{switch_id}'
    HOST_DETAILS = '/menu/details/host/{host_id}'
    SLICE_DETAILS = '/menu/details/slice/{slice_id}'
    NEW_SLICE_DETAILS = '/menu/details/new_slice'
