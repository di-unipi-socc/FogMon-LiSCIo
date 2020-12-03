#!/usr/bin/env python3
from template_fabfile import TestBeds, Ubuntu

class Spec:

   def __init__(self):
      self.start = """<?xml version='1.0'?>
      <rspec xmlns="http://www.geni.net/resources/rspec/3" type="request" generated_by="jFed RSpec Editor" generated="2020-11-30T18:35:22.186+01:00" xmlns:emulab="http://www.protogeni.net/resources/rspec/ext/emulab/1" xmlns:delay="http://www.protogeni.net/resources/rspec/ext/delay/1" xmlns:jfed-command="http://jfed.iminds.be/rspec/ext/jfed-command/1" xmlns:client="http://www.protogeni.net/resources/rspec/ext/client/1" xmlns:jfed-ssh-keys="http://jfed.iminds.be/rspec/ext/jfed-ssh-keys/1" xmlns:jfed="http://jfed.iminds.be/rspec/ext/jfed/1" xmlns:sharedvlan="http://www.protogeni.net/resources/rspec/ext/shared-vlan/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.geni.net/resources/rspec/3 http://www.geni.net/resources/rspec/3/request.xsd ">"""
      self.end = "</rspec>"
      self.spec = {"nodes": {}, "links": {}}

   _id_node_ = 0
   def create_id_node(self):
      ret = self._id_node_
      self._id_node_+=1
      return ret

   _id_link_ = 0
   def create_id_link(self):
      ret = self._id_link_
      self._id_link_+=1
      return ret

   _id_if_ = 0
   def create_id_if(self):
      ret = self._id_if_
      self._id_if_+=1
      return ret

   def setLinkLatCap(self, node1: int, node2:int, latency: int=0, capacity: int=0, packet_loss: str=None):
      links= self.spec["links"]
      for l,v in links.items():
         n1 = v["interfaces"][0].split(":")[0]
         n2 = v["interfaces"][1].split(":")[0]
         if (n1 == "node"+str(node1) and n2 == "node"+str(node2)):
            if latency != 0:
               v["latency"] = latency
            if capacity != 0:
               v["capacity"] = capacity
            if packet_loss is not None:
               v["packet_loss"] = packet_loss


   def create_links(self):
      nodes= self.spec["nodes"]
      links= self.spec["links"]
      for n1,v1 in nodes.items():
         monotonic = False
         for n2,v2 in nodes.items():
            if not monotonic:
               if n1 == n2:
                  monotonic=True
               continue
            same_testbed = False
            if v1["testbed"] == v2["testbed"]:
               same_testbed = True
            id = self.create_id_link()
            if_ = "if"+str(self.create_id_if())
            nodes[n1]["if"].append((if_,same_testbed))
            nodes[n2]["if"].append((if_,same_testbed))
            link_type = "lan"
            if v1["testbed"] == TestBeds.CITY:
               link_type = "gre-tunnel"
            links["link"+str(id)] = {"testbed": v1["testbed"], "interfaces":[n1+":"+if_,n2+":"+if_], "link_type": link_type, "same_testbed": same_testbed, "ips": ["10.%d.%d.%d"%(int(if_[2:])//256, int(if_[2:])%256,int(n1[4:])+1),"10.%d.%d.%d"%(int(if_[2:])//256, int(if_[2:])%256,int(n2[4:])+1)]}


   def create_nodes(self, num: int, testbed: TestBeds):
      nodes= self.spec["nodes"]
      for i in range(num):
         id = self.create_id_node()
         image = Ubuntu.WALL1
         if testbed == TestBeds.WALL2:
            image = Ubuntu.WALL1
         elif testbed == TestBeds.CITY:
            image = Ubuntu.CITY
         nodes["node"+str(id)] = {"testbed": testbed, "image": image,"if": []}

   def print_spec(self):
      text = self.start
      nodes= self.spec["nodes"]
      links= self.spec["links"]
      x = 0
      y = 0
      for n,v in nodes.items():
         text+= '<node client_id="%s" exclusive="true" component_manager_id="%s">\n<sliver_type name="raw-pc">\n<disk_image name="%s"/>\n</sliver_type>\n'%(n,v["testbed"].value,v["image"].value)
         text+= '<location xmlns="http://jfed.iminds.be/rspec/ext/jfed/1" x="%d" y="%d"/>\n'%(x,y)
         x+=10
         y+=10
         for (interface,same_testbed) in v["if"]:
            print(same_testbed,v["testbed"])
            if same_testbed and v["testbed"] != TestBeds.CITY:
               text+= '<interface client_id="%s:%s">\n'%(n,interface)
               text+= '<ip address="10.%d.%d.%d" netmask="255.255.255.0" type="ipv4"/>\n</interface>'%(int(interface[2:])//256, int(interface[2:])%256,int(n[4:])+1)
         # text+= '<services>\n'
         # if v["testbed"] != TestBeds.CITY:
         #    for s in enable_nat:
         #       text+= f'<execute shell="sh" command="{s}"/>\n'
         # for s in docker:
         #    text+= f'<execute shell="sh" command="{s}"/>\n'
         # text+= '</services>\n
         text+= '</node>\n'
      for l,v in links.items():
         if v["testbed"] != TestBeds.CITY:
            if v["same_testbed"]:
               text+= '<link client_id="%s">\n<component_manager name="%s"/>\n'%(l,v["testbed"].value)
               for interface in v["interfaces"]:
                  text+= '<interface_ref client_id="%s"/>\n'%interface
               text+= '<link_type name="%s"/>\n'%v["link_type"]
               
               for interface1 in v["interfaces"]:
                  for interface2 in v["interfaces"]:
                     if not("capacity" in v or "latency" in v or "packet_loss" in v) or interface1 == interface2:
                        continue
                     text+= '<property source_id="%s" dest_id="%s"'%(interface1, interface2)
                     if "capacity" in v:
                        text+= ' capacity="%d"'%v["capacity"]
                     if "latency" in v:
                        text+= ' latency="%d"'%(v["latency"]/2)
                     if "packet_loss" in v:
                        text+= ' packet_loss="%s"'%v["packet_loss"]
                     text+= '/>\n'
               text+= '</link>'
      text+=self.end
      return text

# the first matrix must be symmetric the other represet the upload of every node against another
matrix = [
   ([0,4,10,10],  [0,  0,0  ,0],  TestBeds.WALL2),
   ([4,0,10,10],  [0,  0,0  ,0],  TestBeds.WALL2),
   ([10,10,0,4],  [100,0,0,100],  TestBeds.CITY),
   ([10,10,4,0],  [100,0,100,0],  TestBeds.CITY),
]

spec = Spec()

# spec.create_nodes(2, TestBeds.WALL1)
# spec.create_nodes(1, TestBeds.WALL2)
# spec.create_nodes(2, TestBeds.CITY)

for row in matrix:
   spec.create_nodes(1, row[2])

spec.create_links()

for i in range(len(matrix)):
   for j in range(len(matrix)):
      if i == j:
         continue
      spec.setLinkLatCap(i,j,matrix[i][0][j],matrix[i][1][j])


print(spec.print_spec())
print("\n\n\n")
import json
with open("spec.json","w") as wr:
   json.dump(spec.spec, wr)