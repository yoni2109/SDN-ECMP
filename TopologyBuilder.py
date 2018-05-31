from TopologyReader import *
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.clean import cleanup
from mininet.link import TCLink
import json
from mininet.node import UserSwitch, OVSKernelSwitch, OVSSwitch, IVSSwitch

json_data = read_json('result.json')
with open('graph.json') as jf:
    graph = json.load(jf)
hosts = parse_hosts(json_data)
switches = parse_switches(json_data)
links = parse_links(json_data)

class MultiCastTopology(Topo):
    def __init__(self):
        Topo.__init__(self)

    def build(self):
        for host in hosts:
            # print host.id
            # print host.ip
            # print host.mac
            h = self.addHost(host.id, ip=host.ip, mac=host.mac)

        for switch in switches:
            s = self.addSwitch(switch.id, dpid=str(switch.dpid))            
        
        for link in links:
            l = self.addLink(graph[str(link.node1)]['id'], graph[str(link.node2)]['id'], port1=link.port1, port2=link.port2)
        
print hosts

topot = MultiCastTopology()
net = Mininet(topo=topot, controller=lambda name: RemoteController(name, ip='127.0.0.1', protocol='tcp', port = 6633), link=TCLink )
net.start()
CLI(net)
cleanup()


