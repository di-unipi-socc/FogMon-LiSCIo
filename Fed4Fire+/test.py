#!/usr/bin/env python3
from topology import Topology,Node
from clusterer import Clusterer
from spec import Spec

topology = Topology.load("topology-20-578")
spec = Spec(topology=topology)
spec = spec.spec
S = 0
num = 0
for k,link in spec["links"].items():
    S += link["capacity"]
    num+=1
S/=num
print(S)

T = [(274,275),(249,250),(260,260),(249,250)]

T_avg = []
for (t,r) in T:
    T_avg.append((t/S,t/S))
print(T_avg)
exit()


selected = topology.selected
M = topology.matrix(selected)
clusterer = Clusterer([selected[0]],selected,M[0])
                
data = clusterer.cluster(10000)
print(data)
topology.plot(data["new_leaders"], data["clusters"])