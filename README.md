# sdn-on-demand-slices
SDN On-demand dynamic slicing software using comnetsemu.

This project is realized for the Networking 2 Master course of University of Trento

## Main commands


Listen on switch `s0` on port `6653` and prints output in `test.pcap`
```sh
sudo tcpdump -i s1-eth3
sudo tcpdump -s0 -i lo 'port 6653' -w test.pcap
```

To dump ports of a switch (to view the open-flow table):
```sh
sudo ovs-ofctl show s1
sudo ovs-ofctl dump-flows s1
```
### Proactive add-flow (manual)
```sh
sudo ovs-ofctl add-flow s1 in_port=1,actions=output:2
sudo ovs-ofctl add-flow s1 in_port=2,actions=output:1
```

Quality control service:
```sh
sudo ovs-vsctl set port s1-eth3 qos=@newqos -- \
--id=@newqos create QoS type=linux-htb \
other-config:max-rate=10000000000 \
queues:123=@1q \
queues:234=@2q -- \
--id=@1q create queue other-config:min-rate=10000 other-config:max-rate=500000 -- \
--id=@2q create queue other-config:min-rate=10000 other-config:max-rate=1000000
```


### Flow dynamic control
Starts the manager which redirects incoming traffic dynamically
```sh
ryu-manager simple_switch.py
ryu-manager ryu.app.simple_switch_stp_13
```

## Mininet terminal 

```sh
sudo mn --topo single,3 --mac --switch ovsk --controller remote
```

* Created 3 virtual hosts, each with a separate IP address.
* Created a single OpenFlow software switch in the kernel with 3 ports.
* Connected each virtual host to the switch with a virtual ethernet cable.
* Set the MAC address of each host equal to its IP.
* Configure the OpenFlow switch to connect to a remote controller.

To fix when mininet is not working correctly, first kill mininet and then clear state with:
```sh
quit (to close mininet window)
sudo mn -c (to clear the state)
```

### Mininet window commands
```sh
nodes
help
pingall
h1 ifconfig
h1 ping -c3 h2
iperf h1 h3 (test bandwidth)
sh ovs-ofctl dump-flows s1
xterm h1 h2 (to open host-specific terminal windows)
```

To run a command in background from a specific host (e.g. h3 iperf) inside mininet window:

h1 (client) performs bandwitdh test on h3 (server). The controller service_slicing.py is configured to allow the UDP port 9999 to have a max bandwidth of 10 Mbps. If the port change (e.g. if we put 9998), the max bandwidth drops to 1 Mbps. The following command specify:

* -s / -c: server mode or client mode
* -u: UDP
* -p 9999: port 9999
* -b: bandwidth
* -t: number of tests
* -i: interactive

```sh
h3 iperf -s -u -p 9999 -b 10M & (start listening on h3 as server in background)
h1 iperf -c 10.0.0.3 -u -p 9999 -b 10M -t 10 -i 1 (start sending on h1 as a client)
```

# Documentations

* [Ryu python documentation](https://ryu.readthedocs.io/en/latest/)