#!/usr/bin/env python3
from spec import Spec
from template_fabfile import TestBeds, Ubuntu
import json

# the first and second matrix must be symmetric, the first represent the latency, the other represent the upload of every node against another
# this example create 4 nodes, 2 from WALL2 and 2 from citylab
matrix = [
   ([0,4,10,10],  [0,  0,1000  ,1000],  TestBeds.WALL2),
   ([4,0,10,10],  [0,  0,0  ,      0],  TestBeds.WALL2),
   ([10,10,0,4],  [1000,0,0,    1000],  TestBeds.CITY),
   ([10,10,4,0],  [1000,0,1000,    0],  TestBeds.CITY),
]

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

# print the xml spec
print(spec.print_spec())

# save the spec.json
with open("spec.json","w") as wr:
   json.dump(spec.spec, wr)