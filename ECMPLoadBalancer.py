###################################################
#                                                 #
#                                                 #
#    	THIS IS THE CORRECT VERSION!!!!!!!!!      #
#                                                 #
#                                                 #
###################################################


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

topology_json = read_json("/home/isam/pox/ext/toponetworkx.json")
shortest_paths_json = read_json("/home/isam/pox/ext/shortest_paths.json")

host_ips = {}
host_macs = {}
host_names  = []
for host in topology_json["hosts"]:
    host_ips[host["name"]] = IPAddr(host["ip"])
    host_macs[host["name"]] = EthAddr(host["mac"])
    host_names.append(host["name"])
             
routes = {}

def read_paths(json_data):
    
    for host in json_data: #ips
    	
        temp = {}
        for path in json_data[host]:
            temp[host_ips[path[-1]]] = []
        for path in json_data[host]:
            temp[host_ips[path[-1]]].append([path[1:],0])
            
        routes[host_ips[host]] = temp

read_paths(shortest_paths_json)
#print routes

switch_links = {}

def read_switch_links(json_data):
    
    for element in json_data["links"]:
        switch_links[(element["src"], element["dst"])] = (element["port1"], element["port2"])
        switch_links[(element["dst"], element["src"])] = (element["port2"], element["port1"])

read_switch_links(topology_json)
#print "#####################"
#print switch_links

dpid_to_switch = {}

def save_switch_dpid(json_data):
    
    for elem in json_data["switches"]:
        dpid_to_switch[elem["dpid"].replace(':', '-')] = elem["name"]
        
save_switch_dpid(topology_json)
#print "#####################"
#print dpid_to_switch


connections = {}


def choose_route(src, dst):
    
    flag = 0 
    for path in routes[src][dst]:
        if path[1] == 0:
            flag = 1
    if flag == 0:
        for path in routes[src][dst]:
            path[1] = 0
            
    i = -1
    i = random.randint(0, len(routes[src][dst]) - 1)
    route = routes[src][dst][i]
    
    while route[1] != 0:
        i = random.randint(0, len(routes[src][dst]) - 1)
        route = routes[src][dst][i]
    route[1] = 1
    return route[0]
    

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
		for name in host_names:
                    port = 0
                    for elem in switch_links:
                        if elem[0] == name:
                            port = switch_links[elem][0]
                    self.arpTable[host_ips[name]] = (host_macs[name], port)
                    #print "##############################"
                    #print self.arpTable
		


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#Handle Connection Up
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


	def _handle_ConnectionUp (self, event):

		self.connection = event.connection
                connections[dpid_to_switch[dpidToStr(event.dpid)]] = event.connection
		print "Switch with dpid=%s connected" % dpidToStr(event.dpid) + ", switch name is " + dpid_to_switch[dpidToStr(event.dpid)]
            
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
                        print route
                        print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
                        
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
                            outport = switch_links[(route[i], route[i+1])][0]
                            fm.actions.append(of.ofp_action_output(port=outport))
                            #if event.ofp.buffer_id  != -1 and event.ofp.buffer_id is not None:
                                #fm.buffer_id = event.ofp.buffer_id
                            #elif event.ofp.data is not None:
                            #fm.in_port = inport
                            #fm.data = event.ofp
                            #else:
                                #return
                            connections[route[i]].send(fm)
                            



def launch():
	print "\n======================================================\n"
	print "STARTING LOAD BALANCER"
	print "\n======================================================\n"
	
	core.registerNew(SimpleLoadBalancer)















