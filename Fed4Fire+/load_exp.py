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

with ZipFile(sys.argv[2], 'r') as zipObj:
   # Extract all the contents of zip file in build directory
   zipObj.extractall("build")


with open("template_fabfile.py","r") as rd:
   with open("build/fabfile.py","w") as wr:
      for line in rd.readlines():
         wr.write(line)

with open("build/spec.json","w") as wr:
   json.dump(spec, wr)