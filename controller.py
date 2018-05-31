from pox.core import core
from pox.openflow import *
import pox.openflow.libopenflow_01 as of
from pox.lib.packet.arp import arp
from pox.lib.packet.ipv4 import ipv4
from pox.lib.packet.ethernet import ethernet
from pox.lib.addresses import EthAddr, IPAddr
import time
import random
from pox.lib.recoco import Timer
import numpy as np
import matplotlib.pyplot as plt
from TopologyReader import *
import json
with open('result.json') as jf:
    topo = json.load(jf)
with open('shortest.json') as jf:
    shortest_paths = json.load(jf)
with open('graph.json') as jf:
    graph = json.load(jf)

hosts = {}
ports = {}
routes = {}
connections = {}
switches_dpid = {}

for _ in topo["hosts"]:
    hosts[_['id']] = {}
    hosts[_['id']]['ip'] =IPAddr(_['ip'])
    hosts[_['id']]['mac'] = EthAddr(_['mac'])
    for x in graph:
        if graph[x]['id'] == _['id'] :
            nodeno = x
    hosts[_['id']]['nodeNo'] = nodeno
             
def get_all_shortest_pathes(shortest_paths):   
    for s in shortest_paths:
        # print s
        if graph[s]['isHost']:	
            temp = {}
            for d in shortest_paths[s]:
                if graph[d]['isHost']:
                    temp[graph[d]['ip']] = []
                    for path in shortest_paths[s][d]:
                        temp[graph[d]['ip']].append(path[1:])

            hip =hosts[graph[s]['id']]['ip'] 
        routes[hip] = temp


def init_ports(topo):
    for _ in topo['links']:
        ports[(graph[str(_['node1'])]['id'], graph[str(_['node2'])]['id'])] = (_['port1'], _['port2'])
        ports[(graph[str(_['node2'])]['id'], graph[str(_['node1'])]['id'])] = (_['port2'], _['port1'])

def dpid_to_switch(topo):    
    for _ in topo["switches"]:
        switches_dpid[_['dpid'].replace(':', '-')] = _['id']
    # print switches_dpid
        

def choose_route(src, dst):
    # print src
    # print routes
    route = random.choice(routes[src][str(dst)])
    # print route
    return route

get_all_shortest_pathes(shortest_paths)
init_ports(topo)
dpid_to_switch(topo)

class SimpleLoadBalancer(object):
    
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#Init function
#	service_ip - load balancer ip (input)
#	server_ips - list of server ips (input)
#	arpTable - table with ip addresses and their mac addresses 
#		key: ip
#		value: (mac, port)
#	mapTable - flow rules from clients to severs (init. to empty dict., handeled later in update_lb_mapping)
#		key: client ip
#		value: server ip
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


	def __init__(self): 

		core.openflow.addListeners(self)
		self.arpTable={}
		for h in hosts:
                    port = 0
                    for p in ports:
                        if p[0] == h:
                            port = ports[p][0]
                    self.arpTable[hosts[h]['ip']] = (hosts[h]['mac'], port)
                    #print "##############################"
                    #print self.arpTable
		


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#Handle Connection Up
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


	def _handle_ConnectionUp (self, event):

		self.connection = event.connection
                connections[switches_dpid[dpidToStr(event.dpid)]] = event.connection
		print "Switch with dpid=%s connected" % dpidToStr(event.dpid) + ", switch name is " + switches_dpid[dpidToStr(event.dpid)]
            
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#Handle packet in  
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


	def _handle_PacketIn(self, event):
		
		packet = event.parsed
		connection = event.connection
		inport = event.port
		#print "_handle_PacketIn"
		
		if packet.type != 0x86DD: #ipv6 type
                    print "***************************************************************"
                    print packet 
                    print "***************************************************************"
		
		#ARP TYPE packets
		if packet.type == packet.ARP_TYPE:
		
			#print "ARP PACKET TYPE"
			arp_packet = packet.find('arp')
			
			if arp_packet is not None:
				if arp_packet.opcode == arp.REQUEST:
                                    
                                    #print "arp request"
                                    
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
                                    msg.actions.append(of.ofp_action_output(port = event.port))
                                    connection.send(msg)
                                    
                                    #print "arp reply sent"
                                    
                if packet.type == packet.IP_TYPE:
			
			ip_packet = packet.payload
			ipsrc = ip_packet.srcip
                        ipdst = ip_packet.dstip
                        
                        print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
                        print "Packets sent from " + str(ipsrc) + " to " + str(ipdst) + "\nInstalling path:"
                        route = choose_route(ipsrc, ipdst)
                        # print route
                        print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
                        # print ports
                        for i in range(0, len(route)-1):
                            
                           # src_mac = switch_mac[route[i]] 
                            #dst_mac = switch_mac[route[i+1]] 
                            match1 = of.ofp_match()
                            match1.nw_src = ipsrc
                            match1.nw_dst = ipdst
                            match1.dl_src = self.arpTable[IPAddr(ipsrc)][0] #mac of src host
                            match1.dl_dst = self.arpTable[IPAddr(ipdst)][0] #mac of dst host
                            #match1.dl_src = EthAddr(src_mac)
                            #match1.dl_dst = EthAddr(dst_mac)
                            #match1.inport = self.arpTable[ipsrc][1] #inport of src host
                                    
                            fm = of.ofp_flow_mod()
                            fm.match = match1
                            fm.hard_timeout = 30
                            fm.idle_timeout = 30
                            #fm.actions.append(of.ofp_action_dl_addr.set_src(match1.dl_src))
                            #fm.actions.append(of.ofp_action_dl_addr.set_dst(match1.dl_dst))
                            #fm.actions.append(of.ofp_action_nw_addr.set_dst(ipdst))
                            #outport = self.arpTable[ipdst][1] #outport to dst host
                            outport = ports[(graph[str(route[i])]['id'],graph[str(route[i+1])]['id'])][0]
                            fm.actions.append(of.ofp_action_output(port=outport))
                            #if event.ofp.buffer_id  != -1 and event.ofp.buffer_id is not None:
                                #fm.buffer_id = event.ofp.buffer_id
                            #elif event.ofp.data is not None:
                            #fm.in_port = inport
                            #fm.data = event.ofp
                            #else:
                                #return
                            connections[graph[str(route[i])]['id']].send(fm)
def launch():
    core.registerNew(SimpleLoadBalancer) 
  



#print ports












