import mininet as mn
import networkx as nx
import random
import matplotlib.pyplot as plt
from networkx.readwrite import json_graph as jg
import json
def generate_random_graph():
    g = nx.erdos_renyi_graph(random.randint(1,10),0.2)
    #g.name = 'switches'
    #nx.draw(g)
    #plt.show()
    return g
def generate_switches_graph():
    switches = generate_random_graph()
    for n in switches.node:
        for i in switches.node:
            if not nx.has_path(switches,n,i):
                switches.add_edge(n,i)
    i=0
    for n in switches.node:
        i+=1
        switches.node[n]['id']='s'+str(i)
        switches.node[n]['dpid']='00:00:00:00:00:00:0c:0'+str(i)
        switches.node[n]['isHost'] = False
    for n in switches.node:
        i=1
        neighbors = switches.neighbors(n)
        switches.node[n]['adjacent_switches']={}
        switches.node[n]['adjacent_hosts']={}
        for _ in neighbors:
            switches.node[n]['adjacent_switches'][''+switches.node[_]['id']] = i
            i+=1
    return switches

def generate_hosts(i):
    hosts = nx.Graph()
    #hosts.name = 'hosts'
    x=0
    for _ in range(random.randint(1,i)):
        x+=1
        hosts.add_node(i)
        hosts.node[i]['id'] = 'h'+str(x)
        hosts.node[i]['ip'] = '10.0.0.'+str(x)
        hosts.node[i]['mac'] = '00:00:00:00:00:0'+str(x)
        hosts.node[i]['isHost'] = True
        i+=1
    return hosts



def init_topo():

    switches = generate_switches_graph()
    i=switches.nodes().__len__()+1 
    hosts = generate_hosts(i)
    graph = nx.compose(switches,hosts)
    for h in hosts.node:
        rndnode = random.choice(switches.nodes())
        i= graph.node[rndnode]['adjacent_switches'].values()
        i+=(graph.node[rndnode]['adjacent_hosts'].values())
        if not nx.has_path(graph,h,rndnode):
            graph.add_edge(h,rndnode)
            if i.__len__() > 0:
                graph.node[rndnode]['adjacent_hosts'][graph.node[h]['id']]=max(i)+1
            else:
                graph.node[rndnode]['adjacent_hosts'][graph.node[h]['id']]=1
    #print graph.node
    network = {}
    network['hosts'] = []
    for n in hosts.node:
        network['hosts']+=[hosts.node[n]]
    network['switches'] = []
    for n in graph.node:
        if not graph.node[n]['isHost']:
            network['switches']+=[graph.node[n]]
    network['links'] = []
    ports = {}

    # ports.values()
    # port1
    # port2
    print graph.edges()
    print hosts.nodes()
    for n in graph.edges():
        print n
        if n[1] in hosts.nodes():
            port1 = graph.node[n[0]]['adjacent_hosts'][graph.node[n[1]]['id']]
        else:
            port1 = graph.node[n[0]]['adjacent_switches'][graph.node[n[1]]['id']]
        if n[1] in hosts.nodes():
            port2 = graph.node[n[1]]['adjacent_hosts'][graph.node[n[0]]['id']]
        else:
            port2 = graph.node[n[1]]['adjacent_switches'][graph.node[n[0]]['id']]
        network['links']+=[{'node1':n[0],'node2':n[1],'port1':port1,'port2':port2}]

    
        

    print network

init_topo()
         
