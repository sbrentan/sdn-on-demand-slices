# sdn-on-demand-slices
SDN On-demand dynamic slicing software using comnetsemu.

This project is realized for the Networking 2 Master course of University of Trento and was developed through the combined effort of: [Simone Brentan](https://github.com/sbrentan), [Matteo Costalonga](https://github.com/wamuumu), [Alex Reichert](https://github.com/Faerye0)


# Project setup

This section will go through the steps to set up the project on your local machine.

To run this project locally, you need to have a simulation environment set up where to run Mininet and Ryu controller. As a simulation environment, we suggest using **ComnetSemu**.

ComnetSemu is a virtual machine that runs on VirtualBox and provides a pre-configured environment for network simulations.

## Comnetsemu installation

This project installation and setup has been tested only within a `Windows` environment.

Before starting, make sure you have VirtualBox and Vagrant installed on your machine.
* You can download **Virtualbox** from its offcial [website](https://www.virtualbox.org/).
* You can download **Vagrant** from its official [website](https://www.vagrantup.com/).

To run the virtual machine with ComnetSemu, you can go to this [github repository]("https://github.com/stevelorenz/comnetsemu") and clone it to your local machine.
```sh
git clone https://github.com/stevelorenz/comnetsemu
```

After cloning the repository, you need to setup and build the virtual machine with Vagrant.

Open the Vagrantfile in the cloned repository and add this following line in the correct section.
```vagrantfile
comnetsemu.vm.network "forwarded_port", guest: 8080, host: 8080
```
This is used to forward the port 8080 to the host machine and make the web interface of ComnetSemu accessible from your browser.

Additionally, we suggest to add this line in the Vagrantfile to increase the boot timeout, as the virtual machine takes a while to boot up:
```vagrantfile
config.vm.boot_timeout = 3600
```
You can add this line at around line 102, after the `config.vm.provider "virtualbox"` section.

After modifying the Vagrantfile, you can start the virtual machine by running the following command in the terminal inside the cloned repository:
```sh
vagrant up
```

This will download the necessary files and start the virtual machine. It may take a while, so be patient.

## Project installation

After the virtual machine is up and running, you can access it via SSH with the following command:
```sh
vagrant ssh
```

Once you are inside the virtual machine, go inside the `app` folder in the `comnetsemu` directory:
```sh
cd comnetsemu/app
```

Now you can clone this repository inside the `app` folder:
```sh
git clone https://github.com/sbrentan/sdn-on-demand-slices.git
```

After cloning the repository, go inside the cloned directory and install the necessary dependencies:
```sh
pip install -r requirements.txt
```

Finally, you can start the application by running the apposite launcher script:
```sh
./launcher.sh
```
> !!! Running the launcher script in this way will throw an error, saying that you have to pass the `--net` argument for it to work.
>
> This argument is used to specify the network configuration to apply using `Mininet`. See the following section for more details.

# Running the project

TODO


# General mininet and terminal commands


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
h1 python3 commands/send_packet.py -ip 10.0.0.3 -t udp -p 9999
```

To run a command in background from a specific host (e.g. h3 iperf) inside mininet window:

h1 (client) performs bandwitdh test on h3 (server). The controller service_slicing.py is configured to allow the UDP port 9999 to have a max bandwidth of 10 Mbps. If the port change (e.g. if we put 9998), the max bandwidth drops to 1 Mbps. The following command specify:

* -s / -c: set respectively the server or client mode
* -u: change the protocol from TCP to UDP
* -p 9999: set the port to 9999
* -b 100M: set the upper bound of the bandwidth available (default = 1Mbps) 
* -t: duration of the test (in seconds)
* -i: report interval (in seconds)

```sh
h3 iperf -s -u -p 9999 -b 10M -t 30 & (start listening on h3 as server in background for around 30s)
h1 iperf -c 10.0.0.3 -u -p 9999 -b 10M -t 10 -i 1 (start sending on h1 as a client, 10 times with interval 1s)
```

# Documentations

* [Ryu python documentation](https://ryu.readthedocs.io/en/latest/)