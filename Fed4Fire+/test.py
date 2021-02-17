from topology import Topology
import random
random.seed(83476355) #TODO: change seed

topology = Topology()
topology.create_tree(6,[2,3,2,3,2,1],([(10,20),(1,5),(1,10),(1,30),(1,10)],[(70000,200000),(50000,100000),(10000,100000),(10000,100000),(10,100000)]))
    
cloud_high = random.sample(topology.return_level(2),  1) # Central cloud         3
cloud_low = random.sample(topology.return_level(3),   2) # Decentralised cloud   5
isp = random.sample(topology.return_level(4),         2) # ISP                   12
home = random.sample(topology.return_level(5),        2) # Home                 20
                                                   # =32                        =40
selected = cloud_high + cloud_low + isp + home

topology.purge(selected)
topology.plot([])
topology.save("test.top")


topology2 = Topology.load("test.top")
topology2.plot([])