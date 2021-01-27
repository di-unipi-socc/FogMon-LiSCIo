#!/usr/bin/env python3
import sys
import os
from zipfile import ZipFile
import json

if len(sys.argv)!=3:
   print("use: script.py spec.json filezip.zip")
   exit()

try:
   os.remove("build")
except:
   pass

with open(sys.argv[1], 'r') as rd:
   spec = json.load(rd)

removes = ["node28","node17"] # instert here the list of nodes that failed to run (e.g. "node31")

for remove in removes:
   del spec["nodes"][remove]
   rms = []
   for l,v in spec["links"].items():
      n1 = v["interfaces"][0].split(":")[0]
      n2 = v["interfaces"][1].split(":")[0]
      if n1 == remove or n2 == remove:
         rms.append(l)
   for rm in rms:
      del spec["links"][rm]

with ZipFile(sys.argv[2], 'r') as zipObj:
   # Extract all the contents of zip file in build directory
   zipObj.extractall("build")


with open("template_fabfile.py","r") as rd:
   with open("build/fabfile.py","w") as wr:
      for line in rd.readlines():
         wr.write(line)

os.system("chmod 600 build/id_rsa")

with open("build/spec.json","w") as wr:
   json.dump(spec, wr)