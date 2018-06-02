from pox.core import core
from pox.openflow import *
import pox.openflow.libopenflow_01 as of
from pox.lib.packet.arp import arp
from pox.lib.packet.ethernet import ethernet
from pox.lib.addresses import EthAddr, IPAddr
from pox.lib.util import dpidToStr
import random
import json


hosts = {}
ports = {}
routes = {}
connections = {}
switches_dpid = {}

"""
Handles and parse all JSON files for the reset of the program.
"""
with open('result.json') as jf:
    topo = json.load(jf)
with open('shortest.json') as jf:
    shortest_paths = json.load(jf)
with open('graph.json') as jf:
    graph = json.load(jf)


def set_hosts():
    """
    This method responsible placing hosts in the current network topology.
    """
    for _ in topo['hosts']:
        node = None

        hosts[_['id']] = {}
        hosts[_['id']]['ip'] = IPAddr(_['ip'])
        hosts[_['id']]['mac'] = EthAddr(_['mac'])

        for x in graph:
            if graph[x]['id'] == _['id']:
                node = x

        hosts[_['id']]['nodeNo'] = node


def fix_dpid_switch():
    """
    This method fixes the dpid of each switch in the current network topology.
    """
    for _ in topo['switches']:
        switches_dpid[_['dpid'].replace(':', '-')] = _['id']


def init_ports():
    """
    This method initializes each of the ports to which each network component (hosts and switches) is connected.
    """
    for _ in topo['links']:
        ports[(graph[str(_['node1'])]['id'], graph[str(_['node2'])]['id'])] = (_['port1'], _['port2'])
        ports[(graph[str(_['node2'])]['id'], graph[str(_['node1'])]['id'])] = (_['port2'], _['port1'])


def get_shortest_paths():
    """
    This method calculates all the shortest paths in this correct topology.
    """
    temp = None
    hip = None

    for s in shortest_paths:
        if graph[s]['isHost']:
            temp = {}
            for d in shortest_paths[s]:
                if graph[d]['isHost']:
                    temp[graph[d]['ip']] = []
                    for path in shortest_paths[s][d]:
                        temp[graph[d]['ip']].append(path[1:])

            hip = hosts[graph[s]['id']]['ip']
        routes[hip] = temp  # Updates routes dictionary.


def select_route(src, dst):
    """
    This method selects one of the shortest paths from the dictionary with all the shortest paths.

    :return: Chooses and returns the shortest route from the dictionary.
    """
    return random.choice(routes[src][str(dst)])


class ECMPBalancer(object):

    def __init__(self):

        core.openflow.addListeners(self)
        self.arpTable = {}
        for h in hosts:
            port = 0
            for p in ports:
                if p[0] == h:
                    port = ports[p][0]
            self.arpTable[hosts[h]['ip']] = (hosts[h]['mac'], port)

    def _handle_ConnectionUp(self, event):

        self.connection = event.connection
        connections[switches_dpid[dpidToStr(event.dpid)]] = event.connection
        print 'Switch with dpid=%s connected' % dpidToStr(event.dpid) + ', as ' + switches_dpid[dpidToStr(event.dpid)]

    def _handle_PacketIn(self, event):

        packet = event.parsed
        connection = event.connection

        if packet.type != 0x86DD:   # IPV6 packet type
            pass

        if packet.type == packet.ARP_TYPE:

            arp_packet = packet.find('arp')
            print 'ARP TYPE'
            if arp_packet is not None:
                if arp_packet.opcode == arp.REQUEST:
                    arp_reply = arp()
                    arp_reply.opcode = arp.REPLY
                    arp_reply.hwsrc = EthAddr(self.arpTable[IPAddr(arp_packet.protodst)][0])
                    arp_reply.hwdst = arp_packet.hwsrc
                    arp_reply.hwtype = arp.HW_TYPE_ETHERNET
                    arp_reply.prototype = arp.PROTO_TYPE_IP
                    arp_reply.hwlen = 6
                    arp_reply.protolen = 4
                    arp_reply.protosrc = arp_packet.protodst
                    arp_reply.protodst = arp_packet.protosrc

                    e = ethernet()
                    e.set_payload(arp_reply)
                    e.type = ethernet.ARP_TYPE
                    e.src = EthAddr(self.arpTable[IPAddr(arp_packet.protodst)][0])
                    e.dst = arp_packet.hwsrc

                    msg = of.ofp_packet_out()
                    msg.data = e.pack()
                    msg.actions.append(of.ofp_action_output(port=event.port))
                    connection.send(msg)

        if packet.type == packet.IP_TYPE:
            ip_packet = packet.payload
            ipsrc = ip_packet.srcip
            ipdst = ip_packet.dstip

            print 'Installing path for ' + str(ipsrc) + ' -> ' + str(ipdst)

            route = select_route(ipsrc, ipdst)  # Chooses shortest route from the dictionary.

            for i in range(0, len(route) - 1):
                match1 = of.ofp_match()
                match1.nw_src = ipsrc
                match1.nw_dst = ipdst
                match1.dl_src = self.arpTable[IPAddr(ipsrc)][0]  # MAC of source host.
                match1.dl_dst = self.arpTable[IPAddr(ipdst)][0]  # MAC of destination host.

                fm = of.ofp_flow_mod()
                fm.match = match1
                fm.hard_timeout = 30
                fm.idle_timeout = 30
                fm.actions.append(of.ofp_action_nw_addr.set_dst(ipdst))

                outport = ports[(graph[str(route[i])]['id'], graph[str(route[i + 1])]['id'])][0]
                fm.actions.append(of.ofp_action_output(port=outport))

                connections[graph[str(route[i])]['id']].send(fm)

    def _handle_ConnectionDown(self, event):
        print 'Switch %s going down' % dpidToStr(event.dpid)


def launch():
    set_hosts()                       # Sets hosts for current network topology.
    get_shortest_paths()              # Calculates all shortest paths in network topology.
    init_ports()                      # Initializes ports of network components.
    fix_dpid_switch()                 # fixes the dpid of switches.
    core.registerNew(ECMPBalancer)    # Run controller.
