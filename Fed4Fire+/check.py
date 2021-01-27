#!/usr/bin/env python3
from pyclustering.cluster.kmedoids import kmedoids
from pyclustering.cluster import cluster_visualizer
from pyclustering.utils import read_sample
from pyclustering.samples.definitions import FCPS_SAMPLES
import random
import math
import sqlite3

def avg_dist(matrix,cluster,medoid):
    m = 0
    for i in cluster:
        if i==medoid:
            continue
        m+= matrix[i][medoid]
    if len(cluster)==1:
        return 0
    return m/(len(cluster)-1)

def quality(matrix,clusters,medoids):
    v = 0
    avgs = [avg_dist(matrix,clusters[i],medoids[i]) for i in range(len(medoids))]
    for i in range(len(medoids)):
        m = 0
        for j in range(len(medoids)):
            if i==j:
                continue
            m2 = (avgs[i]+avgs[j])/matrix[medoids[i]][medoids[j]]
            if m < m2:
                m = m2
        v += m
    return v/len(medoids)

class Clusterer:
    def __init__(self, Ls,Ns, Links):
        self.Nodes = Ns
        self.Leaders = Ls

        self.N = len(self.Nodes)
        self.L = len(self.Leaders)

        self.D = {}
        for i in range(self.N):
            self.D[self.Nodes[i]]=i

        self.A = [[Links[i][j] for j in self.Nodes] for i in self.Nodes]

        k = int(math.sqrt(self.N))
        # Set random initial medoids. considering the already selected leaders
        if self.L<k:
            sample = []
            for i in range(len(self.A)):
                if i not in [self.D[i] for i in self.Leaders]:
                    sample.append(i)
            self.initial_medoids = [self.D[i] for i in self.Leaders] + random.sample(sample,k=k-self.L)
        elif self.L==k:
            self.initial_medoids = [self.D[i] for i in self.Leaders]
        else:
            self.initial_medoids = random.sample([self.D[i] for i in self.Leaders],k=k)

    def cluster(self):

        # create K-Medoids algorithm for processing distance matrix instead of points
        kmedoids_instance = kmedoids(self.A, self.initial_medoids, data_type='distance_matrix')
        # run cluster analysis and obtain results
        kmedoids_instance.process()
        medoids = kmedoids_instance.get_medoids()
        clusters = kmedoids_instance.get_clusters()
        q = quality(self.A,clusters,medoids)



        new_leaders = []

        for i in self.D:
            if self.D[i] in medoids:
                new_leaders.append(i)
        
        changes = 0

        for i in new_leaders:
            if i not in self.Leaders:
                changes+=1

        data = {
            "quality": q,
            "new_leaders": new_leaders,
            "changes": changes
            }

        return data


if __name__ == "__main__":
    import json

    print("Number of leaders? (then 1 leader per line)")
    L = int(input())
    Leaders = []
    for _ in range(L):
        Leaders.append(input().replace("\n",""))

    with open("spec.json", 'r') as rd:
        spec = json.load(rd)
    
    Nodes = [k for k,v in spec["nodes"].items()]

    Links = {}
    for i in Nodes:
        Links[i] = {}
        for j in Nodes:
            Links[i][j] = 0

    for l,v in spec["links"].items():
        n1 = v["interfaces"][0].split(":")[0]
        n2 = v["interfaces"][1].split(":")[0]
        try:
            Links[n1][n2] = v["latency"]
            Links[n2][n1] = v["latency"]
        except:
            Links[n1][n2] = 0

    probs = {}
    for i in Nodes:
        probs[i] = 0
    
    probs = {}
    qual = {}
    q_min = 100
    q_max = 0

    Num = 10000
    for _ in range(Num):
        clusterer = Clusterer([Nodes[0]],Nodes,Links)
        
        data = clusterer.cluster()
        
        if len(data["new_leaders"]) != len(Leaders):
            raise Exception("Wrong number of leaders!!!")
        inside = True
        for l in Leaders:
            if l not in data["new_leaders"]:
                inside = False
                break
        if inside:
            print("Configuration is OK!!!")
            break
        
        #qual[tuple(data["new_leaders"])] = data["quality"]

        if q_min > data["quality"]:
            q_min = data["quality"]
        
        if q_max < data["quality"]:
            q_max = data["quality"]

        for l in data["new_leaders"]:
            probs[l] = probs.get(l,0) +1
    
    for i in probs:
        probs[i] /= Num
    
    print(q_max,q_min)

    
    probs = {k: v for k, v in sorted(probs.items(), key=lambda item: item[1], reverse=True) if v != 0}
    print(probs)
    qual = {k: v for k, v in sorted(qual.items(), key=lambda item: item[1]) if v < 3}
    print(qual)