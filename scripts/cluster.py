#!/usr/bin/env python3
from pyclustering.cluster.kmedoids import kmedoids
from pyclustering.cluster import cluster_visualizer
from pyclustering.utils import read_sample
from pyclustering.samples.definitions import FCPS_SAMPLES
import random
import math
import sqlite3
import sys

if len(sys.argv) != 2:
    exit()

try:
    formula = int(sys.argv[1])
except:
    exit()

from shutil import copyfile

copyfile("leader_node.db", "leader_node_copy.db")

conn = sqlite3.connect('leader_node_copy.db')
c = conn.cursor()

Nodes = c.execute('SELECT * FROM MNodes').fetchall()
Leaders = c.execute('SELECT * FROM MMNodes').fetchall()

L = len(Leaders)
LeadersIds = []
for i in Leaders:
    LeadersIds.append(str(i[0]))

N = len(Nodes)

D = {}
for i in range(N):
    D[str(Nodes[i][0])]=i

A = [[None for _ in range(N)] for _ in range(N)]

avg = 0
n = 0
for a in c.execute('SELECT * FROM MLinks'):
    try:
        A[D[str(a[0])]][D[str(a[1])]] = a[2]
        if a[2] != None:
            avg += a[2]
            n+=1
    except:
        pass

c.close()

avg /= n
for i in range(len(A)):
    for j in range(len(A[i])):
        if A[i][j]==None:
            A[i][j] = avg
        if A[i][j]==0:
            A[i][j] = 0.5

from clusterer import Clusterer
clusterer = Clusterer([D[i] for i in LeadersIds],[D[str(i[0])] for i in Nodes],A, formula)

data = clusterer.cluster(2)
import json

print(json.dumps(data))