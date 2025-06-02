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

To run the virtual machine with ComnetSemu, you can go to this [github repository](https://github.com/stevelorenz/comnetsemu) and clone it to your local machine.
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
You can add this line at around line 102, after the `config.vm.provider "virtualbox"` section. This will increase the boot timeout to 1 hour, which should be enough for the virtual machine to start up.

After modifying the Vagrantfile, you can start the virtual machine by running the following command in the terminal inside the cloned repository:
```sh
vagrant up
```

This will download the necessary files and start the virtual machine. It may take a while, so be patient.

> **Note**: After running the `vagrant up` command the terminal may hang for a while and sometimes it freezes. It can be useful to open the VirtualBox application manually (just opening the application should be enough) to unfreeze the terminal.

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

Install mininet and the openvswitch package for `superuser`:
```sh
sudo apt update
sudo apt install openvswitch-switch
sudo apt install mininet
```

After cloning the repository, go inside the cloned directory and install the necessary dependencies:
```sh
sudo pip install -r requirements.txt
```

Finally, you can start the application by running the apposite launcher script:
```sh
./launcher.sh
```

## Launcher errors

If, when running the launcher script, you get an error like this:
```bash
$ ./launcher.sh
-bash: ./launcher.sh: /bin/bash^M: bad interpreter: No such file or directory
```
 
It means you need to fix the end of line characters in the `launcher.sh` file from `CLRF` to `LF`. This can be done with the following command:
```sh
sed -i 's/\r$//' launcher.sh
```

Instead, if you get an error like this:
```bash
$ ./launcher.sh
Error: --net argument is required. Possible values are: 1, 2, 3.
```

This is correct and expected behavior, as the launcher script requires a network configuration to be specified in order to run the application.

This argument is used to specify the network configuration to apply using `Mininet`. See the following section for more details.


# Running the project

Three different demo scenarios have been implemented in this project, each with its own network configuration. You can run them by passing the `--net` argument to the launcher script, where the possible values are `1`, `2` or `3`. For example:
```sh
./launcher.sh --net 1
```

This will start the application with the first network configuration, which is a simple topology with 4 hosts and 4 switches.

The output of the command will be something like this:
```bash
vagrant@comnetsemu:~/comnetsemu/app/sdn-on-demand-slices$ ./launcher.sh --net 1
Starting Ryu controller...
Starting Mininet network...

Waiting for all nodes to be correctly set up and available...
Attempt 2/5...
All nodes are ready.

Polling APIs for packets requests...
mininet>
```

After starting the application, what basically happens is the following:
* The Ryu controller is started, which is responsible for managing the network and handling the OpenFlow messages.
* Mininet is started and the network is created with the specified configuration, which creates the virtual hosts and switches.
* The controller waits for all nodes to be correctly set up and available, which may take a few seconds. To do this, it tries to ping all hosts in the network until they are reachable.
    * This takes a while because the network becomes available only after all the nodes/switches are connected and the Ryu controller handled the creation of the queues and flows.
* A thread is started from within the Mininet executable (`Polling APIs for packets requests...`) that polls the Ryu controller for packets requests. This is used for sending custom packets to the network and to monitor the traffic.

When closing the application, you can do it by pressing `Ctrl + D` in the terminal or by typing `exit` in the Mininet console. This will stop the Mininet network and the Ryu controller, and exit the application. Additionally, it will run the `mn -c` command to clear the Mininet state, which is useful to avoid issues when restarting the application.

# Application GUI

The application provides a simple web interface to interact with the network and send custom packets. You can access it by opening your browser and going to `http://localhost:8080`.

You will see something like this:

![Application GUI](images/application_gui.png)

* The left side of the interface shows a menu with the list of slices created in the network. The `New Slice +` button allows you to create a new slice. The green circle next to each slice indicates that the slice is active, while a red circle indicates that the slice is inactive.
* The center of the interface shows the network topology, with the hosts and switches connected to each other.
* In the top-right corner, there are some buttons to control the network canvas, such as zooming in and out, resetting the view, and saving the current topology displacement. This is useful to keep the topology in a specific position when refreshing the page.
* Under the page title, there is a button that allows you to send a packet in the network and monitor its traffic. More details on this in the following [Sending a packet](#sending-a-packet) section.

When clicking either a `slice` in the left menu or anything in the network topology (`host`, `switch` or `link`), the right side of the interface shows the details of the selected element.

If you click on a `slice`, you will see something like this:

![Slice details](images/slice_menu.png)

## Details Menus

The possible details menus are:

![Slice details](images/details_menus.png)

In the `Host` and `Switch` details menus, you can edit the name of the element, which is useful to identify it in the network topology. You can also see the Datapath ID for the switch and the IP/MAC address for the host.

In the `Link` details menu, you can see the name of the two nodes connected as well as the list of slices that are using that link. This is useful to understand which slices are sharing the same link and which bandwidth they are using.

In the `Slice` details menu, you can see the name of the slice and the minumum/maximum bandwidth that the slice can use (expressed in `bits/sec`). You can also see a list of **RULES** that are applied to the slice, which are used to filter the traffic and apply the bandwidth limits. The rules are explained in more detail in the next section. In this menu, in addition to the `Edit` button, there is also a `Delete` button that allows you to delete the slice and a `Enable/Disable` button that allows you to enable or disable the slice. When a slice is disabled, it will not be able to send or receive traffic, but it will still be present in the network and can be enabled again later.

## Slice Rules

The slice rules are used to filter the traffic and define which packets are allowed to pass through the slice. Three types of rules are available:

* **PROTOCOL**: This rule allows you to filter the traffic based on the protocol used in the packet. You can select from a list of protocols (TCP, UDP, ICMP).
* **PORT**: This rule allows you to filter the traffic based on the port used in the packet.
* **SERVICE**: This rule allows you to filter the traffic based on the service the packet needs to reach. As shown in the above image, a service is defined by a combination of ip address and a list of ports. This is useful to define a specific service that the slice can access, such as a web server or a database.

> **SERVICES** have been introduced as a different mechanism to allow packets to pass. In particular, this type of rule only needs either the sender or the receiver to match the service, while the other host is not checked.

> A simple combination of **PROTOCOL** and **PORT** rules would instead require both the sender and the receiver to match the same protocol and port, which is not always desired.

In order for a packet to be allowed to pass through the slice, it must match **ALL** the rules defined in it. For example, if you define a slice with a PROTOCOL rule set to TCP and a PORT rule set to 80, only TCP packets on port 80 will be allowed to pass through the slice.

## Editing a slice

When clicking the `Edit` button in the slice details menu, you can edit the name of the slice, the minimum and maximum bandwidth (expressed in `bits/sec`), and the list of rules applied to the slice.

![Editing a slice](images/edit_slice.png)

You can add a new rule by clicking the `+` button next to each list of rules. This will open a modal window where you can insert the details of the rule. If you want to delete a rule, you can click the `x` button next to the rule in the list.

When you are done editing the slice, you can click the `Confirm` button to save the changes. The slice will be updated in the network and the new rules will be applied to the traffic.

> Both when editing a slice and when enabling/disabling/deleting it, the page will show a loading spinner while the changes are being applied to the network. This is because the Ryu controller needs to update the OpenFlow rules and queues in the switches and this may take a few seconds.

## Adding a new slice

To create a new slice, you can click the `New Slice +` button in the left menu. This will open the right side menu with the details of the new slice, but it also allows the user to select the hosts and switches that will be part of the slice. The selected hosts and switches will be highlighted in the network topology.

![Creating a slice](images/create_slice.gif)

After selecting the hosts and switches, you can edit the name of the slice, the minimum and maximum bandwidth (expressed in `bits/sec`), and the list of rules applied to the slice. The rules can be added by clicking the `+` button next to each list of rules, as explained in the previous section.

When you are done creating the slice, you can click the `Confirm New Slice` button  in the left menu to save the new slice. The slice will be added to the network and the new rules will be applied to the traffic.

> In the same way that happens when editing a slice, a loading spinner will be shown to wait for the Ryu controller to update the OpenFlow rules and queues in the switches.

## Sending a packet

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