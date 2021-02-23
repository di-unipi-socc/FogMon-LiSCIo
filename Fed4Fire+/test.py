#!/usr/bin/env python3
from topology import Topology,Node
from clusterer import Clusterer

topology = Topology.load("topology-20-226")
selected = topology.selected
M = topology.matrix(selected)
clusterer = Clusterer([selected[0]],selected,M[0])
                
data = clusterer.cluster(10000)
print(data)
topology.plot(data["new_leaders"], data["clusters"])