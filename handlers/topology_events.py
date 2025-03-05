from ryu.controller.handler import set_ev_cls
from ryu.topology import event

import logging, time

class TopologyEventHandler:

    hosts: set = set()
    switches: set = set()
    links: set = set()
    last_event_time = None

    @property
    def connected_hosts(self):
        return len(self.hosts)
    
    @property
    def connected_switches(self):
        return len(self.switches)

    # TODO: find a way to avoid ghost hosts / switches
    
    @set_ev_cls(event.EventHostAdd)
    def host_add_handler(self, ev):
        host = ev.host
        logging.info(f'Host detected: {host}')
        if host.mac not in self.hosts:
            self.hosts.add(host.mac)
            self.last_event_time = time.time()
            logging.info('Host added: %s', host.mac)

    @set_ev_cls(event.EventHostDelete)
    def host_delete_handler(self, ev):
        host = ev.host
        if host.mac in self.hosts:
            self.hosts.remove(host.mac)
            self.last_event_time = time.time()
            logging.info('Host deleted: %s', host.mac)

    @set_ev_cls(event.EventSwitchEnter)
    def switch_enter_handler(self, ev):
        switch = ev.switch
        if switch.dp.id not in self.switches:
            self.switches.add(switch.dp.id)
            self.last_event_time = time.time()
            logging.info('Switch entered: %s', switch.dp.id)
    
    @set_ev_cls(event.EventSwitchLeave)
    def switch_leave_handler(self, ev):
        switch = ev.switch
        if switch.dp.id in self.switches:
            self.switches.remove(switch.dp.id)
            self.last_event_time = time.time()
            logging.info('Switch left: %s', switch.dp.id)
    
