class Host(object):
    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "ID = %s, IP = %s, MAC = %s" % (self.id, self.ip, self.mac)



class Switch(object):
    def __init__(self):
        self.adjacent_switches = {}
        self.adjacent_hosts = {}

    def __str__(self):
        return self.id

    def __repr__(self):
        return self.id

    def is_entry(self, src, dst):
        (s, d) = (str(src), str(dst))
        if (s, d) in self.routing_table:
            return True
        else:
            return False

    def get_entry(self, src, dst):
        (s, d) = (str(src), str(dst))

        return self.routing_table[(s, d)]

    def set_entry(self, src, dst, outports):
        (s, d) = (str(src), str(dst))

        self.routing_table[(s, d)] = outports

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)


class Link(object):
    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "(Node = %s, Port = %s) <--> (Node = %s, Port = %s)" % (self.node1, self.port1, self.node2, self.port2)

    def __eq__(self, other):
        nodes = (self.node1 == other.node1 and self.node2 == other.node2)
        ports = (self.port1 == other.port1 and self.port2 == other.port2)

        return nodes and ports