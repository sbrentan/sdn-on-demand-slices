from ryu.controller.handler import set_ev_cls
from ryu.topology import event

import logging, time

class TopologyEventHandler:

    connected_hosts: int = 0
    connected_switches: int = 0
    connected_links: int = 0
    last_event_time = None
    
    @set_ev_cls(event.EventHostAdd)
    def host_add_handler(self, ev):
        host = ev.host
        self.connected_hosts += 1
        self.last_event_time = time.time()
        logging.info('Host added: %s', host.mac)

    @set_ev_cls(event.EventHostDelete)
    def host_delete_handler(self, ev):
        host = ev.host
        self.connected_hosts -= 1
        self.last_event_time = time.time()
        logging.info('Host deleted: %s', host.mac)

    @set_ev_cls(event.EventSwitchEnter)
    def switch_enter_handler(self, ev):
        switch = ev.switch
        self.connected_switches += 1
        self.last_event_time = time.time()
        logging.info('Switch entered: %s', switch.dp.id)
    
    @set_ev_cls(event.EventSwitchLeave)
    def switch_leave_handler(self, ev):
        switch = ev.switch
        self.connected_switches -= 1
        self.last_event_time = time.time()
        logging.info('Switch left: %s', switch.dp.id)

    @set_ev_cls(event.EventLinkAdd)
    def link_add_handler(self, ev):
        link = ev.link
        self.connected_links += 1
        self.last_event_time = time.time()
        logging.info('Link added: %s', link)
    
    @set_ev_cls(event.EventLinkDelete)
    def link_delete_handler(self, ev):
        link = ev.link
        self.connected_links -= 1
        self.last_event_time = time.time()
        logging.info('Link deleted: %s', link)
