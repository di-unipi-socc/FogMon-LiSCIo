#!/usr/bin/env python3
import random
import math

class Node:
    def __init__(self,id):
        self.id = id
        self.childs = []
        self.costs = []
    
    def add_child(self,node, cost):
        self.childs.append(node)
        self.costs.append(cost)
    
    def remove_child(self, idx):
        del self.childs[idx]
        del self.costs[idx]

class Topology: 
    def __init__(self):
        self.id = 0

    def create_tree_(self,n,l, costs):
        id = self.id
        self.id+=1
        if n <= 0:
            return Node(id)
        tree = Node(id)
        for i in range(l[n-1]):
            mean = (costs[n-2][0]+costs[n-2][1])/2
            lat = int(random.randrange(costs[n-2][0],costs[n-2][1]))
            if (abs(lat-mean) < mean//2):
                lat = int(random.randrange(costs[n-2][0],costs[n-2][1]))
            tree.add_child(self.create_tree_(n-1,l,costs),lat)       
        return tree

    def create_tree(self,n, l,costs):
        self.tree = self.create_tree_(n,l[::-1],costs[::-1])

    def return_level(self, n):
        expanded = [self.tree]
        for _ in range(n):
            tmp = []
            for i in expanded:
                tmp += i.childs
            expanded = tmp
        selected = []
        for i in expanded:
            selected.append(i.id)
        return selected

    def search_path_(self,tree, id):
        if tree.id == id:
            return ([id],[])
        if not tree.childs:
            return None
        for child,cost in zip(tree.childs,tree.costs):
            res = self.search_path_(child,id)
            if res is not None:
                return ([tree.id]+res[0], [cost]+res[1])
    
    def search_path(self, id):
        return self.search_path_(self.tree,id)
    
    def purge_(self, tree, els):
        remove = []
        for i in range(len(tree.childs)):
            if tree.childs[i].id not in els:
                remove.append(i-len(remove))
        
        for i in remove:    
            tree.remove_child(i)
        
        for child in tree.childs:
            self.purge_(child, els)

    def purge(self, selected):
        els = []
        for id in selected:
            path = self.search_path(id)
            els+=path[0]
        self.purge_(self.tree,els)
        return els

    def sum_path(self, a, b):
        path = self.search_path(a)
        path2 = self.search_path(b)
        sum = 0
        while len(path[0]) < len(path2[0]):
            path[0].append(-1)
            path[1].append(0)
        while len(path2[0]) < len(path[0]):
            path2[0].append(-1)
            path2[1].append(0)
            
        for a,b,c,d in zip(path[0][1:],path2[0][1:],path[1],path2[1]):
            if a!=b:
                sum+=c+d
        return sum
    
    def matrix(self, selected):
        M = {}
        for i in selected:
            M[i] = {}
            for j in selected:
                if i==j:
                    M[i][j] = 0
                M[i][j] = self.sum_path(i,j)
        return M
    
if __name__ == "__main__":

    def print_tree_(T,tree):
        T.add_node(tree.id)
        for child,cost in zip(tree.childs,tree.costs):
            T.add_node(child.id)
            T.add_edge(tree.id,child.id, l=cost)
            print_tree_(T,child)

    def print_tree(tree):
        T = nx.DiGraph()
        print_tree_(T, tree)
        return T

    import matplotlib.pyplot as plt
    import networkx as nx
    import pydot
    from networkx.drawing.nx_pydot import graphviz_layout
    from check import Clusterer

    topology = Topology()
    topology.create_tree(6,[2,3,2,3,2,1],[(10,20),(1,5),(1,10),(1,30),(1,10)])
    selected = []
    cloud_high = random.sample(topology.return_level(2),  3) # Central cloud         3
    cloud_low = random.sample(topology.return_level(3),   5) # Decentralised cloud   5
    isp = random.sample(topology.return_level(4),         12) # ISP                   12
    home = random.sample(topology.return_level(5),        20) # Home                 20
                                                    # =32                        =40
    selected = cloud_high + cloud_low + isp + home

    print(len(selected))
    els = topology.purge(selected)
    els.sort()
    els = list(dict.fromkeys(els))
    T=print_tree(topology.tree)

    N1 = 4
    N2 = 5
    path = topology.search_path(selected[N1])
    path2 = topology.search_path(selected[N2])
    sum = 0
    for a,b,c,d in zip(path[0][1:],path2[0][1:],path2[1],path2[1]):
        if a!=b:
            sum+=c+d
    print(sum)
    print(path)
    print(path2)
    print(topology.sum_path(selected[N1],selected[N2]))
    print(topology.id)

    M = topology.matrix(selected)
    for i in selected:
        for j in selected:
            if i==j:
                continue
            if M[i][j] == 0:
                print(i,M[i])

    min = 10
    data = None
    for _ in range(100):
        clusterer = Clusterer([selected[0]],selected,M)
            
        data_ = clusterer.cluster()
        if data_["quality"] < min:
            min = data_["quality"]
            data = data_
        
    print(data)
    pos = graphviz_layout(T, prog="dot")
    nx.draw_networkx(T, pos, node_color=["yellow" if i in data["new_leaders"]else "pink" if i in selected else "#000000" for i in els])
    nx.draw_networkx_edge_labels(T, pos)
    plt.show()
    print("save?")
    y = input()
    if y in ["yes","y"]:
        from spec import Spec
        from template_fabfile import TestBeds, Ubuntu
        import json
        matrix = []
        for i in selected:
            latencies = [M[i][j] for j in selected]
            uploads = [100000//M[i][j] if i!=j and M[i][j]!=0 else 0 for j in selected] # TODO add better values
            testbed = TestBeds.WALL2 if i not in home else TestBeds.CITY
            matrix.append((latencies,uploads,testbed))
        spec = Spec()

        # spec.create_nodes(2, TestBeds.WALL1)
        # spec.create_nodes(1, TestBeds.WALL2)
        # spec.create_nodes(2, TestBeds.CITY)

        # this take the matrix and create the nodes
        for row in matrix:
            spec.create_nodes(1, row[2])

        # instantiate the links
        spec.create_links()

        # set the link informations
        for i in range(len(matrix)):
            for j in range(len(matrix)):
                if i == j:
                    continue
                spec.setLinkLatCap(i,j,matrix[i][0][j],matrix[i][1][j])

        # save the xml spec
        with open("spec.xml","w") as wr:
            wr.write(spec.print_spec())

        # save the spec.json
        with open("spec.json","w") as wr:
            json.dump(spec.spec, wr)