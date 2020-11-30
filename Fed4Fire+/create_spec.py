#!/usr/bin/env python3
from enum import Enum
from xml.dom import minidom
import xml.etree.ElementTree as ET

class TestBeds(Enum):
   WALL1 = "urn:publicid:IDN+wall1.ilabt.iminds.be+authority+cm"
   WALL2 = "urn:publicid:IDN+wall2.ilabt.iminds.be+authority+cm"
   CITY = "urn:publicid:IDN+lab.cityofthings.eu+authority+cm"

class Spec:

   def __init__(self):
      self.start = """<?xml version='1.0'?>
      <rspec xmlns="http://www.geni.net/resources/rspec/3" type="request" generated_by="jFed RSpec Editor" generated="2020-11-30T18:35:22.186+01:00" xmlns:emulab="http://www.protogeni.net/resources/rspec/ext/emulab/1" xmlns:delay="http://www.protogeni.net/resources/rspec/ext/delay/1" xmlns:jfed-command="http://jfed.iminds.be/rspec/ext/jfed-command/1" xmlns:client="http://www.protogeni.net/resources/rspec/ext/client/1" xmlns:jfed-ssh-keys="http://jfed.iminds.be/rspec/ext/jfed-ssh-keys/1" xmlns:jfed="http://jfed.iminds.be/rspec/ext/jfed/1" xmlns:sharedvlan="http://www.protogeni.net/resources/rspec/ext/shared-vlan/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.geni.net/resources/rspec/3 http://www.geni.net/resources/rspec/3/request.xsd ">"""
      self.end = "</rspec>"

      self.nodes = ""
      self.links = ""
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

   def create_interface(self, node):
      max = -1
      for interface in node["if"]:
         id = int(interface[2:])
         if id > max:
            max = id
      id = "if"+str(max+1)
      node["if"].append(id)
      return id

   def setLinkLatCap(self, node1: int, node2:int, latency: int=None, capacity: int=None, packet_loss: str=None):
      links= self.spec["links"]
      for l,v in links.items():
         n1 = v["interfaces"][0].split(":")[0]
         n2 = v["interfaces"][1].split(":")[0]
         if (n1 == "node"+str(node1) and n2 == "node"+str(node2)) or (n2 == "node"+str(node1) and n1 == "node"+str(node2)):
            if latency is not None:
               v["latency"] = latency
            if capacity is not None:
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
            if v1["testbed"] == v2["testbed"]:
               id = self.create_id_link()
               if1 = self.create_interface(nodes[n1])
               if2 = self.create_interface(nodes[n2])
               link_type = "lan"
               if v1["testbed"] == TestBeds.CITY:
                  link_type = "gre-tunnel"
               links["link"+str(id)] = {"testbed": v1["testbed"], "interfaces":[n1+":"+if1,n2+":"+if2], "link_type": link_type}


   def create_nodes(self, num: int, testbed: TestBeds):
      nodes= self.spec["nodes"]
      for i in range(num):
         id = self.create_id_node()
         nodes["node"+str(id)] = {"testbed": testbed, "if": []}

   def print_spec(self):
      text = self.start
      nodes= self.spec["nodes"]
      links= self.spec["links"]
      for n,v in nodes.items():
         text+= '<node client_id="%s" component_manager_id="%s">\n<sliver_type name="raw-pc"/>\n'%(n,v["testbed"].value)
         for interface in v["if"]:
            text+= '<interface client_id="%s:%s">\n<ip address="192.168.0.%d" netmask="255.255.255.0" type="ipv4"/>\n</interface>'%(n,interface, int(n[4:])+1)
         text+= '</node>\n'
      for l,v in links.items():
         text+= '<link client_id="%s">\n<component_manager name="%s"/>\n'%(l,v["testbed"].value)
         for interface in v["interfaces"]:
            text+= '<interface_ref client_id="%s"/>\n'%interface
         text+= '<link_type name="%s"/>\n'%v["link_type"]
         if v["testbed"] != TestBeds.CITY:
            for interface1 in v["interfaces"]:
               for interface2 in v["interfaces"]:
                  if not("capacity" in v or "latency" in v or "packet_loss" in v):
                     continue
                  text+= '<property source_id="%s" dest_id="%s"'%(interface1, interface2)
                  if "capacity" in v:
                     text+= ' capacity="%d"'%v["capacity"]
                  if "latency" in v:
                     text+= ' latency="%d"'%v["latency"]
                  if "packet_loss" in v:
                     text+= ' packet_loss="%s"'%v["packet_loss"]
                  text+= '/>\n'
         text+= '</link>'
      text+=self.end
      return text


spec = Spec()

spec.create_nodes(2, TestBeds.WALL1)
spec.create_nodes(3, TestBeds.WALL2)
spec.create_nodes(3, TestBeds.CITY)

spec.create_links()

spec.setLinkLatCap(0,1,10,100)


print(spec.print_spec())
print("\n\n\n")
print(spec.spec)