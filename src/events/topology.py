import abc
import logging

from ryu.controller.handler import set_ev_cls
from ryu.topology import event

from utils import QueueUtils


# TODO: updated with initialization request on slice adding (or when loading from file)


class TopologyEventHandler(abc.ABC):

    @set_ev_cls(event.EventHostAdd)
    def host_add_handler(self, ev):
        host = ev.host
        logging.info('Host added: %s', host.mac)
        self.update_topology()

    @set_ev_cls(event.EventHostDelete)
    def host_delete_handler(self, ev):
        host = ev.host
        logging.info('Host deleted: %s', host.mac)
        self.update_topology()

    @set_ev_cls(event.EventSwitchEnter)
    def switch_enter_handler(self, ev):
        switch = ev.switch
        logging.info('Switch entered: %s', switch.dp.id)
        QueueUtils.set_ovsdb_address(switch.dp.id) # TODO: needed with OVSDB bridge?
        self.update_topology()

    @set_ev_cls(event.EventSwitchLeave)
    def switch_leave_handler(self, ev):
        switch = ev.switch
        logging.info('Switch left: %s', switch.dp.id)
        self.update_topology()

    @set_ev_cls(event.EventLinkAdd)
    def link_add_handler(self, ev):
        link = ev.link
        logging.info('Link added: %s', link)
        self.update_topology()

    @set_ev_cls(event.EventLinkDelete)
    def link_delete_handler(self, ev):
        link = ev.link
        logging.info('Link deleted: %s', link)
        self.update_topology()

    # TODO: get links doesn't count for host - switch connections. Add port events or something else?

    @abc.abstractmethod
    def update_topology(self):
        raise NotImplementedError
