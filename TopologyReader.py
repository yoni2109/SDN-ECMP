from NetworkStructures import *
import simplejson as json
import copy

def read_json(filename):
    with open(filename) as json_file:
        data = json.load(json_file)
    return data


def parse_hosts(data):
    hosts = []

    for host in data['hosts']:
        h = Host()
        h.ip = host['ip']
        h.mac = host['mac']
        h.id = host['id']

        hosts.append(h)

    return hosts


def parse_switches(data):
    switches = []

    for switch in data['switches']:
        s = Switch()
        s.id = switch['id']
        s.dpid = switch['dpid']
        s.dpidstr = s.dpid[6:].replace(':', '-')
        s.adjacent_switches = switch['adjacent_switches']
        s.adjacent_hosts = switch['adjacent_hosts']

        switches.append(s)

    return switches


def parse_links(data):
    links = []

    for link in data['links']:
        l = Link()
        l.node1 = link['node1']
        l.node2 = link['node2']
        l.port1 = link['port1']
        l.port2 = link['port2']

        links.append(l)

    return links

