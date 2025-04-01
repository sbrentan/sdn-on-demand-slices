import logging

from ryu.topology.switches import Switch

from common.constants import FlowPriority, DSCP_TAG_VALUE


class PacketUtils:

    @staticmethod
    def add_flow(datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        # Set table_id to 1 for the QoS 
        mod = parser.OFPFlowMod(
            datapath=datapath, table_id=1, priority=priority, match=match, instructions=inst
        )
        datapath.send_msg(mod)

    @staticmethod
    def delete_flow(datapath, match):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        mod = parser.OFPFlowMod(
            datapath=datapath, table_id=1, command=ofproto.OFPFC_DELETE, out_port=ofproto.OFPP_ANY,
            out_group=ofproto.OFPG_ANY, match=match
        )
        datapath.send_msg(mod)

    @staticmethod
    def delete_flows(switch: Switch):
        ofproto = switch.dp.ofproto
        parser = switch.dp.ofproto_parser
        match = switch.dp.ofproto_parser.OFPMatch()

        logging.info(f"Deleting flows for switch {switch.dp.id}")

        # Delete all flows
        PacketUtils.delete_flow(switch.dp, match)

        # Add table-miss flow entry
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        PacketUtils.add_flow(switch.dp, FlowPriority.TABLE_MISS.value, match, actions)
        
        # Add monitored packet flow entry
        match = parser.OFPMatch(eth_type=0x0800, ip_dscp=DSCP_TAG_VALUE >> 2)  # IPv4 with DSCP 32
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        priority = FlowPriority.MONITORED_PACKET.value
        logging.info(f"Adding flow with priority {priority} and match {match}")
        PacketUtils.add_flow(switch.dp, priority, match, actions)

    @staticmethod
    def send_package(msg, datapath, in_port, actions):
        data = None
        ofproto = datapath.ofproto
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data,
        )
        datapath.send_msg(out)
