#!/usr/bin/env python3
import argparse
import grpc
import os
import sys
from time import sleep
import yaml

# Import P4Runtime lib from parent utils dir
sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 '/home/p4/tutorials/utils/'))

from scapy.layers.inet import IP, TCP
from scapy.layers.l2 import Ether

from sswitch_runtime import SimpleSwitch
from sswitch_runtime.ttypes import *

import p4runtime_lib.bmv2
from p4runtime_lib.error_utils import printGrpcError
from p4runtime_lib.switch import ShutdownAllSwitchConnections
import p4runtime_lib.helper
from p4runtime_lib.simple_controller import insertCloneGroupEntry

# Load switches and keys json files
def load_switches_conf(ssl):
    data = {}
    keys=[]
    with open('./config/switches.json', 'r') as json_file:
        #data = json.load(json_file)
        data = yaml.safe_load(json_file)
    if ssl:
        with open('./config/keys.json', 'r') as json_file:
            data2 = yaml.safe_load(json_file)
        keys = data2['keys']
    return data,keys

# Initial configuration of switches
def connect_to_switches(switches_config, ssl, keys):
    switches = []
    for switch in switches_config:
        if (ssl is not True):
            switches.append(
                p4runtime_lib.bmv2.Bmv2SwitchConnection(
                    name=switch["name"],
                    address=switch["address"],
                    device_id=switch["device_id"],
                    proto_dump_file=switch["proto_dump_file"]))
        else:
            switches.append(
                p4runtime_lib.bmv2.Bmv2SwitchConnection(
                    name=switch["name"],
                    address=switch["address"],
                    device_id=switch["device_id"],
                    proto_dump_file=switch["proto_dump_file"],
                    channel=ssl,
                    cacert = keys[0],
                    cert=keys[1],
                    private_key=keys[2]
                    ))

    return switches

def send_master_arbitration_updates(switches):
    for switch in switches:
        switch.MasterArbitrationUpdate()

def set_pipelines(switches, p4info_helper, bmv2_file_path):
    for switch in switches:
        switch.SetForwardingPipelineConfig(p4info=p4info_helper.p4info, bmv2_json_file_path=bmv2_file_path)
        print("Installed P4 Program using SetForwardingPipelineConfig on %s" % switch.name)


def writeRules(p4info_helper, switches, switches_conf):
    """
    Installs six rules:
    1) An routing rule of every switch to forward packets to the specified port
    2) A Pot ingress rule on the ingress switch that adds OPoT headers and performs OPoT calculations
    3) A PoT forward rule on middles nodes that performs OPoT calculations
    4) A PoT egress rule on the egress switch that removes OPoT headers and performs OPoT calculations
    5) A metrics rule that builds a packets with metrics to be sent to the collector
    6) An clone rule that clones the packet to send OPoT packet and metrics packet

    It also builds a clone group entry on port 3 (collector) for cloned packets
    """

    for idx, sw in enumerate(switches):
        switch = switches_conf[idx]

        # 0) Default Routes
        table_entry = p4info_helper.buildTableEntry(
            table_name="PoT.routing_table",
            default_action=True,
            action_name="PoT.drop")
        sw.WriteTableEntry(table_entry)
        print("Installed default routing rule on %s" % sw.name)

        table_entry = p4info_helper.buildTableEntry(
            table_name="PoT.t_pot",
            default_action=True,
            action_name="PoT.drop")
        sw.WriteTableEntry(table_entry)
        print("Installed default OPoT rule on %s" % sw.name)

        # 1) Routing rule
        for rule in switch["routing_rules"]:
            table_entry = p4info_helper.buildTableEntry(
                table_name="PoT.routing_table",
                match_fields={
                    "hdr.inner_ipv4.dstAddr": (rule["match"]["dstAddr"], rule["match"]["prefix_len"]),
                    "standard_metadata.ingress_port": rule["match"]["ingress_port"]
                },
                action_name="PoT.ipv4_forward",
                action_params={
                    "srcAddr": rule["action_params"]["srcAddr"],
                    "dstAddr": rule["action_params"]["dstAddr"],
                    "port": rule["action_params"]["port"]
                })
            sw.WriteTableEntry(table_entry)
            print("Installed routing rule on %s" % sw.name)

        # 2) Pot Ingress Rule
        for rule in switch["pot_ingress_rules"]:
            table_entry = p4info_helper.buildTableEntry(
                table_name="PoT.t_pot",
                match_fields={
                    "hdr.nshPot.servicePathIdentifier": rule["match"]["servicePathIdentifier"],
                    "hdr.nshPot.serviceIndex": rule["match"]["serviceIndex"],
                    "hdr.ipv4.dstAddr": rule["match"]["dstAddr"]
                },
                action_name="PoT.pot_ingress",
                action_params={
                    "prime": rule["action_params"]["prime"],
                    "identifier": rule["action_params"]["identifier"],
                    "serviceIndex": rule["action_params"]["serviceIndex"],
                    "secretShare": rule["action_params"]["secretShare"],
                    "publicPol": rule["action_params"]["publicPol"],
                    "lpc": rule["action_params"]["lpc"],
                    "upstreamMask": rule["action_params"]["upstreamMask"],
                    "magic_M": rule["action_params"]["magic_M"],
                    "magic_a": rule["action_params"]["magic_a"],
                    "magic_s": rule["action_params"]["magic_s"]
                })
            sw.WriteTableEntry(table_entry)
            print("Installed PoT ingress rule on %s" % sw.name)

        # 3) Pot Forward Rule
        for rule in switch["pot_forward_rules"]:
            table_entry = p4info_helper.buildTableEntry(
                table_name="PoT.t_pot",
                match_fields={
                    "hdr.nshPot.servicePathIdentifier": rule["match"]["servicePathIdentifier"],
                    "hdr.nshPot.serviceIndex": rule["match"]["serviceIndex"],
                    "hdr.ipv4.dstAddr": rule["match"]["dstAddr"]
                },
                action_name="PoT.pot_forward",
                action_params={
                    "prime": rule["action_params"]["prime"],
                    "secretShare": rule["action_params"]["secretShare"],
                    "publicPol": rule["action_params"]["publicPol"],
                    "lpc": rule["action_params"]["lpc"],
                    "upstreamMask": rule["action_params"]["upstreamMask"],
                    "downstreamMask": rule["action_params"]["downstreamMask"],
                    "magic_M": rule["action_params"]["magic_M"],
                    "magic_a": rule["action_params"]["magic_a"],
                    "magic_s": rule["action_params"]["magic_s"]
                })
            sw.WriteTableEntry(table_entry)
            print("Installed PoT forward rule on %s" % sw.name)

        # 4) Pot Egress Rule
        for rule in switch["pot_egress_rules"]:
            table_entry = p4info_helper.buildTableEntry(
                table_name="PoT.t_pot",
                match_fields={
                    "hdr.nshPot.servicePathIdentifier": rule["match"]["servicePathIdentifier"],
                    "hdr.nshPot.serviceIndex": rule["match"]["serviceIndex"],
                    "hdr.ipv4.dstAddr": rule["match"]["dstAddr"]
                },
                action_name="PoT.pot_egress",
                action_params={
                    "prime": rule["action_params"]["prime"],
                    "secretShare": rule["action_params"]["secretShare"],
                    "publicPol": rule["action_params"]["publicPol"],
                    "lpc": rule["action_params"]["lpc"],
                    "validator_key": rule["action_params"]["validator_key"],
                    "downstreamMask": rule["action_params"]["downstreamMask"],
                    "magic_M": rule["action_params"]["magic_M"],
                    "magic_a": rule["action_params"]["magic_a"],
                    "magic_s": rule["action_params"]["magic_s"]
                })
            sw.WriteTableEntry(table_entry)
            print("Installed PoT egress rule on %s" % sw.name)
        
        # 5) Metrics Egress Rule
        for rule in switch["metrics_rules"]:
            table_entry = p4info_helper.buildTableEntry(
                table_name="MyEgress.metrics_table",
                action_name="MyEgress.send_metrics",
                action_params={
                    "srcAddr": rule["action_params"]["srcAddr"],
                    "dstAddr": rule["action_params"]["dstAddr"],
                    "port": rule["action_params"]["port"],
                    "ipSrcAddr": rule["action_params"]["ipSrcAddr"],
                    "ipDstAddr": rule["action_params"]["ipDstAddr"]
                })
            sw.WriteTableEntry(table_entry)
            print("Installed Metrics egress rule on %s" % sw.name)

        # 6) Clone Rule
        for rule in switch["clone_rules"]:
            table_entry = p4info_helper.buildTableEntry(
                table_name="PoT.clone_table",
                match_fields={
                    "hdr.inner_ipv4.dstAddr": (rule["match"]["dstAddr"], rule["match"]["prefix_len"]),
                    "standard_metadata.ingress_port": rule["match"]["ingress_port"]
                },
                action_name="PoT.do_clone"
                )
            sw.WriteTableEntry(table_entry)
            print("Installed Clone rule on %s" % sw.name)

        # Rule for cloning packets to cpu port
        rule={
            "clone_session_id":1,
            "replicas": [
                {
                    "egress_port": 3,
                    "instance": 1
                }
            ]
                
        }
        insertCloneGroupEntry(sw, rule, p4info_helper)

def print_ipv4_address(address,min,max):
    return str(int.from_bytes(address[min:max],"big"))

def readTableRules(p4info_helper, switches):
    """
    Reads the table entries from all tables on the switch.
    :param p4info_helper: the P4Info helper
    :param sw: the switch connection
    """
    for idx, sw in enumerate(switches):
        print('\n----- Reading tables rules for %s -----' % sw.name)
        for response in sw.ReadTableEntries():
            for entity in response.entities:
                entry = entity.table_entry
                table_name = p4info_helper.get_tables_name(entry.table_id)
                # Print Table Name
                print('\n%s: ' % table_name, end=' ')
                for m in entry.match:
                    # Print Match Field Name
                    print(p4info_helper.get_match_field_name(table_name, m.field_id), end=' ')
                    if(type(p4info_helper.get_match_field_value(m)) is not tuple):
                        hex_string = p4info_helper.get_match_field_value(m).hex()
                        if len(hex_string) == 8:
                            formatted_string = '.'.join(str(int(hex_string[i:i+2],16)) for i in range(0, len(hex_string), 2))
                        else:
                            formatted_string = ':'.join(hex_string[i:i+2] for i in range(0, len(hex_string), 2))
                        # Print Match Field Value (MAC Address / IPv Address)
                        print(formatted_string, end=' ')
                    else:
                        address = p4info_helper.get_match_field_value(m)[0]
                        # Print Match Field Value (IPv4 address)
                        print(print_ipv4_address(address,0,1)+"."+print_ipv4_address(address,1,2)+"."+print_ipv4_address(address,2,3)+"."+print_ipv4_address(address,3,4), end=' ')  
                action = entry.action.action
                action_name = p4info_helper.get_actions_name(action.action_id)
                # Print Action Name
                print('\n->', action_name, end=' ')
                for p in action.params:
                    print(p4info_helper.get_action_param_name(action_name, p.param_id), end=' ')
                    hex_string = p.value.hex()
                    if len(hex_string) == 12:
                        formatted_string = ':'.join(hex_string[i:i+2] for i in range(0, len(hex_string), 2))
                        # Print Action Value (MAC Address)
                        print(formatted_string, end=' ')
                    else:
                        # Print Action Value
                        print(int.from_bytes((p.value),"big"), end=' ')
                print()

def main(p4info_file_path, bmv2_file_path, ssl):
    # Instantiate a P4Runtime helper from the p4info file
    p4info_helper = p4runtime_lib.helper.P4InfoHelper(p4info_file_path)

    switches_conf,keys = load_switches_conf(ssl)

    try:
        # Create a switch connection object for switches;
        # this is backed by a P4Runtime gRPC connection.
        # Also, dump all P4Runtime messages sent to switch to given txt files.
        switches = connect_to_switches(switches_conf["switches"],ssl, keys)

        # Send master arbitration update message to establish this controller as
        # master (required by P4Runtime before performing any other write operation)
        print(switches_conf["switches"])
        send_master_arbitration_updates(switches)

        # Install the P4 program on the switches
        set_pipelines(switches, p4info_helper, bmv2_file_path)

        # Write the rules into the tables
        writeRules(p4info_helper, switches, switches_conf["switches"])

        # Read rules from tables
        readTableRules(p4info_helper, switches)

    except KeyboardInterrupt:
        print(" Shutting down.")
    except grpc.RpcError as e:
        printGrpcError(e)

    ShutdownAllSwitchConnections()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='P4Runtime Controller')
    parser.add_argument('--p4info', help='p4info proto in text format from p4c',
                        type=str, action="store", required=True)
    parser.add_argument('--bmv2-json', help='BMv2 JSON file from p4c',
                        type=str, action="store", required=True)
    parser.add_argument('--ssl',
                    help='Use secure SSL/TLS gRPC channel to connect to the P4Runtime server',
                    action='store_true')
    args = parser.parse_args()

    if not os.path.exists(args.p4info):
        parser.print_help()
        print("\np4info file not found" % args.p4info)
        parser.exit(1)
    if not os.path.exists(args.bmv2_json):
        parser.print_help()
        print("\nBMv2 JSON file not found" % args.bmv2_json)
        parser.exit(1)
    main(args.p4info, args.bmv2_json, args.ssl)