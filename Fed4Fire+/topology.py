#!/usr/bin/env python3
import random
import math
import pickle

# session 2: seed 7574
#
random.seed(83476355) #TODO: change seed

# TODO: display colors for groups
# TODO: save topology for change

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
            cost = []
            for e in costs:
                e = e[::-1]
                mean = (e[n-2][0]+e[n-2][1])/2
                el = int(random.randrange(e[n-2][0],e[n-2][1]))
                if (abs(el-mean) < mean//2):
                    el = int(random.randrange(e[n-2][0],e[n-2][1]))
                cost.append(el)
            tree.add_child(self.create_tree_(n-1,l,costs),cost)       
        return tree

    def create_tree(self,n, l,costs):
        self.tree = self.create_tree_(n,l[::-1],costs)

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
        self.selected = selected
        els = []
        for id in selected:
            path = self.search_path(id)
            els+=path[0]
        self.purge_(self.tree,els)
        els.sort()
        self.routers = list(dict.fromkeys(els))
        return self.routers

    def sum_path(self, a, b):
        path = self.search_path(a)
        path2 = self.search_path(b)
        sum = 0
        mini = 1000000000000
        while len(path[0]) < len(path2[0]):
            path[0].append(-1)
            path[1].append([0,mini])
        while len(path2[0]) < len(path[0]):
            path2[0].append(-1)
            path2[1].append([0,mini])
        
        for a,b,c,d in zip(path[0][1:],path2[0][1:],path[1],path2[1]):
            if a!=b:
                sum+=c[0]+d[0]
                mini = min(mini,min(c[1],d[1]))
        return (sum,mini)
    
    def matrix(self, selected):
        M = [{},{}]
        for i in selected:
            M[0][i] = {}
            M[1][i] = {}
            for j in selected:
                if i==j:
                    M[0][i][j] = 0
                    M[1][i][j] = 0
                cost = self.sum_path(i,j)
                M[0][i][j] = cost[0]
                M[1][i][j] = cost[1]
        return M
    
    def save(self, path):
        with open(path,"wb") as file:
            pickle.dump(self, file)
    
    @staticmethod
    def load(path):
        with open(path,"rb") as file:
            data = pickle.load(file)
            return data

    def plot(self, leaders):
        import matplotlib.pyplot as plt
        import networkx as nx
        import pydot
        from networkx.drawing.nx_pydot import graphviz_layout
        def print_tree_(T,tree):
            T.add_node(tree.id)
            for child,cost in zip(tree.childs,tree.costs):
                T.add_node(child.id)
                T.add_edge(tree.id,child.id, l=cost[0],b=cost[1])
                print_tree_(T,child)

        def print_tree(tree):
            T = nx.DiGraph()
            print_tree_(T, tree)
            return T
        T=print_tree(self.tree)
        pos = graphviz_layout(T, prog="dot")
        nx.draw_networkx(T, pos, node_color=["yellow" if i in leaders else "pink" if i in self.selected else "#000000" for i in self.routers])
        nx.draw_networkx_edge_labels(T, pos)
        plt.show()

if __name__ == "__main__":

    from clusterer import Clusterer

    topology = Topology()
    topology.create_tree(6,[2,3,2,3,2,1],([(10,20),(1,5),(1,10),(1,30),(1,10)],[(70000,200000),(50000,100000),(10000,100000),(10000,100000),(10,100000)]))
    selected = []
    cloud_high = random.sample(topology.return_level(2),  1) # Central cloud         3
    cloud_low = random.sample(topology.return_level(3),   2) # Decentralised cloud   5
    isp = random.sample(topology.return_level(4),         2) # ISP                   12
    home = random.sample(topology.return_level(5),        2) # Home                 20
                                                    # =32                        =40
    selected = cloud_high + cloud_low + isp + home

    print(len(selected))
    topology.purge(selected)

    N1 = 4
    N2 = 5
    path = topology.search_path(selected[N1])
    path2 = topology.search_path(selected[N2])
    print(path)
    print(path2)
    print(topology.sum_path(selected[N1],selected[N2]))
    print(topology.id)

    M = topology.matrix(selected)
    for i in selected:
        for j in selected:
            if i==j:
                continue
            if M[0][i][j] == 0:
                print(i,M[i])

    min = 10
    data = None
    for _ in range(100):
        clusterer = Clusterer([selected[0]],selected,M[0])
            
        data_ = clusterer.cluster()
        if data_["quality"] < min:
            min = data_["quality"]
            data = data_
    
    #TODO insert colors for clusters
    print(data)
    topology.plot(data["new_leaders"])
    print("save?")
    y = input()
    if y in ["yes","y"]:
        topology.save("topology")
        from spec import Spec
        from template_fabfile import TestBeds, Ubuntu
        import json
        matrix = []
        for i in selected:
            latencies = [M[0][i][j] for j in selected]
            uploads = [M[1][i][j] for j in selected]
            testbed = TestBeds.WALL2 if i not in home else TestBeds.CITY
            matrix.append((latencies,uploads,testbed))
        spec = Spec()

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