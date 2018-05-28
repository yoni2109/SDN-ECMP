from TopologyReader import *
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.clean import cleanup
from mininet.link import TCLink
from mininet.node import UserSwitch, OVSKernelSwitch, OVSSwitch, IVSSwitch


json_data = read_json('topology_sample.json')
hosts = parse_hosts(json_data)
switches = parse_switches(json_data)
links = parse_links(json_data)

class MultiCastTopology(Topo):
    def __init__(self):
        Topo.__init__(self)

    def build(self):
        for host in hosts:
            h = self.addHost(host.id, ip=host.ip, mac=host.mac)

        for switch in switches:
            s = self.addSwitch(switch.id, dpid=str(switch.dpid))            
        
        for link in links:
            l = self.addLink(link.node1, link.node2, port1=link.port1, port2=link.port2)
        

topo = MultiCastTopology()
net = Mininet( topo=topo, controller=lambda name: RemoteController(name, ip='127.0.0.1', protocol='tcp', port = 6633), link=TCLink )
net.start()
CLI(net)
cleanup()

