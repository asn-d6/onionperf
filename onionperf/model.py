'''
  OnionPerf
  Authored by Rob Jansen, 2015
  Copyright 2015-2020 The Tor Project
  See LICENSE for licensing information
'''

from abc import ABCMeta, abstractmethod
from io import StringIO
from networkx import read_graphml, write_graphml, DiGraph

class TGenModel(object, metaclass=ABCMeta):
    '''
    an action-dependency graph model for Shadow's traffic generator
    '''

    def dump_to_string(self):
        s = StringIO()
        write_graphml(self.graph, s)
        return s.getvalue()

    def dump_to_file(self, filename):
        write_graphml(self.graph, filename)

class TGenLoadableModel(TGenModel):

    def __init__(self, graph):
        self.graph = graph

    @classmethod
    def from_file(cls, filename):
        graph = read_graphml(filename)
        model_instance = cls(graph)
        return model_instance

    @classmethod
    def from_string(cls, string):
        s = StringIO()
        s.write(string)
        graph = read_graphml(s)
        model_instance = cls(graph)
        return model_instance

class TGenModelConf(object):
    """Represents a TGen traffic model configuration."""
    def __init__(self, initial_pause=0, num_transfers=1, transfer_size="5 MiB",
                 continuous_transfers=False, inter_transfer_pause=5, port=None, servers=[],
                 socks_port=None):
        self.initial_pause = initial_pause
        self.num_transfers = num_transfers
        self.transfer_size = transfer_size
        self.continuous_transfers = continuous_transfers
        self.inter_transfer_pause = inter_transfer_pause
        self.port = port
        self.servers = servers
        self.socks_port = socks_port


class GeneratableTGenModel(TGenModel, metaclass=ABCMeta):

    @abstractmethod
    def generate(self):
        pass

class ListenModel(GeneratableTGenModel):

    def __init__(self, tgen_port="8888"):
        self.tgen_port = tgen_port
        self.graph = self.generate()

    def generate(self):
        g = DiGraph()
        g.add_node("start", serverport=self.tgen_port, loglevel="info", heartbeat="1 minute")
        return g


class TorperfModel(GeneratableTGenModel):

    def __init__(self, config):
        self.config = config
        self.graph = self.generate()

    def generate(self):
        server_str = ','.join(self.config.servers)
        g = DiGraph()

        if self.config.socks_port is not None:
            g.add_node("start",
                       serverport=self.config.port,
                       peers=server_str,
                       loglevel="info",
                       heartbeat="1 minute",
                       socksproxy="127.0.0.1:{0}".format(self.config.socks_port))
        else:
            g.add_node("start",
                       serverport=self.config.port,
                       peers=server_str,
                       loglevel="info",
                       heartbeat="1 minute")

        g.add_node("pause", time="%d seconds" % self.config.initial_pause)
        g.add_edge("start", "pause")

        # "One-shot mode," i.e., onionperf will stop after the given number of
        # iterations.  The idea is:
        # start -> pause -> stream-1 -> pause-1 -> ... -> stream-n -> pause-n -> end
        g.add_node("stream",
                   sendsize="0",
                   recvsize=self.config.transfer_size,
                   timeout="15 seconds",
                   stallout="10 seconds")
        g.add_node("pause_between",
                   time="%d seconds" % self.config.inter_transfer_pause)

        g.add_edge("pause_initial", "stream")

        # only add an end node if we need to stop
        if self.config.continuous_transfers:
            # continuous mode, i.e., no end node
            g.add_edge("stream", "pause_between")
        else:
            # one-shot mode, i.e., end after configured number of transfers
            g.add_node("end",
                       count=str(self.config.num_transfers))
            # check for end condition after every transfer
            g.add_edge("stream", "end")
            # if end condition not met, pause
            g.add_edge("end", "pause_between")

        g.add_edge("pause_between", "stream")

        return g


def dump_example_tgen_torperf_model(domain_name, onion_name):
    # the server listens on 8888, the client uses Tor to come back directly, and using a hidden serv
    server = ListenModel(tgen_port="8888")
    public_server_str = "{0}:8888".format(domain_name)
    onion_server_str = "{0}:8890".format(onion_name)
    client = TorperfModel(tgen_port="8889", socksproxy="localhost:9001", tgen_servers=[public_server_str, onion_server_str])

    # save to specified paths
    server.dump_to_file("tgen.server.torperf.graphml.xml")
    client.dump_to_file("tgen.client.torperf.graphml.xml")
