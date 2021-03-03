#!/usr/bin/env python3
import requests
from spec import Spec
from testbed import Testbed
from topology import Topology, Node
import copy
from time import sleep
from datetime import datetime
from zipfile import ZipFile
import random

# TODO: retry all connections error exceptions
configs = {
    "default": {   
        "--time-report": 30,
        "--time-tests": 30,
        "--leader-check": 8,
        "--time-latency": 30,
        "--time-bandwidth": 600,
        "--heartbeat": 90,
        "--time-propagation": 20,
        "--max-per-latency": 100,
        "--max-per-bandwidth": 3,
        "--sensitivity": 15,
        "--hardware-window": 20,
        "--latency-window": 10,
        "--bandwidth-window": 5,
        "-t": 5,
    },
    "reactive": {   
        "--time-report": 15,
        "--time-tests": 15,
        "--leader-check": 4,
        "--time-latency": 15,
        "--time-bandwidth": 120,
        "--heartbeat": 45,
        "--time-propagation": 10,
        "--max-per-latency": 100,
        "--max-per-bandwidth": 3,
        "--sensitivity": 10,
        "--hardware-window": 10,
        "--latency-window": 5,
        "--bandwidth-window": 3,
        "-t": 5,
    }
}

class Experimenter:
    def __init__(self, base_topology):
        self.sessions = []
        self.base_topology = base_topology
        self.used_topology = copy.deepcopy(base_topology)
        self.removed = []
        self.num = len(self.base_topology.selected)
        self.testbed = Testbed("build")

    def clear_session(self, session):
        r = requests.get(f"http://131.114.72.76:8248/testbed/{session}/remove")
        if r.status_code != 200:
            raise Exception("connection error")

    def start_session(self, name):
        self.spec = Spec(topology=self.used_topology)
        self.spec.remove_nodes(self.removed)
        spec = self.spec.spec
        num = len(spec["nodes"])

        spec["id"] = len(self.sessions)
        r = requests.post("http://131.114.72.76:8248/testbed", json=spec)
        if r.status_code != 201:
            raise Exception("connection error")
        session = r.json()["session"]
        self.sessions.append({"num": num, "name": name, "session": session, "moments": [],"version": 1})
        self.clear_session(session)
        print("session",self.sessions[-1])
        import json
        with open("sessions.json","w") as wr:
            json.dump(self.sessions, wr)

    def start_moment(self, name):
        spec = self.spec.spec
        r = requests.post(f"http://131.114.72.76:8248/testbed/{self.sessions[-1]['session']}", json=spec)
        if r.status_code != 201:
            raise Exception("connection error")
            
        self.sessions[-1]["moments"]
        import json
        with open("sessions.json","w") as wr:
            json.dump(self.sessions, wr)
        
    def build_params(self, conf):
        conf["-s"] = self.sessions[-1]["session"]
        conf["-i"] = "131.114.72.76:8248"
        params = ""
        for param,val in conf.items():
            params += f"{param} {val} "
        return params

    def setup(self):
        spec = Spec(topology=self.base_topology).spec
        self.testbed.setup(spec)

    def start_fogmon(self, conf):
        spec = self.spec.spec
        followers = [k for k in spec["nodes"]]
        params = self.build_params(conf)
        self.testbed.start(followers=followers[1:],leader=followers[0],params=params)

    def stop_fogmon(self):
        spec = self.spec.spec
        nodes = [k for k in spec["nodes"]]
        self.testbed.stop(nodes)
        import json
        with open("sessions.json","w") as wr:
            json.dump(self.sessions, wr)

    def get_roles(self):
        r = requests.get(f"http://131.114.72.76:8248/testbed/{self.sessions[-1]['session']}")
        if r.status_code != 200:
            raise Exception("connection error")
        data = r.json()["data"]
        nodes = {v["id"]:v["name"] for v in data["d3"]["nodes"]}
        self.leaders = [nodes[v["source"]] for v in data["d3"]["links"] if v["source"]==v["target"]]
        self.followers = {nodes[v["source"]]:nodes[v["target"]] for v in data["d3"]["links"] if v["source"]!=v["target"]}
        print("get roles")

    def wait_stability(self):
        stable = False
        start_time = datetime.now()
        while not stable:
            sleep(60)
            try:
                r = requests.get(f"http://131.114.72.76:8248/testbed/{self.sessions[-1]['session']}/accuracy")
                if r.status_code != 200:
                    raise Exception("connection error")
                moments = r.json()["data"]
                moment = moments[-1]
                if "True" in moment["stable"] or "False (3)" in moment["stable"]:
                    stable = True
                    self.get_roles()
            except:
                pass
            time_delta = datetime.now() - start_time
            if time_delta.total_seconds() >= 60*40:
                break
        print(f"stable: {stable}", flush=True)
        if not stable:
            exit(1)
        return stable

    def kill_nodes(self, leaders, followers, moment = True):
        # leaders: number of leaders to kill
        # followers: number of followers to kill
        nodes = []
        nodes += random.sample(self.leaders,leaders)
        nodes += random.sample(list(self.followers),followers)
        self.testbed.kill(nodes)
        self.removed += nodes
        self.spec.remove_nodes(self.removed)
        if moment:
            self.start_moment(f"kill {leaders} {followers}, {nodes}")

    def restart_nodes(self, nodes, conf, moment = True):
        self.removed = [v for v in self.removed if v not in nodes]
        self.spec = Spec(topology=self.used_topology)
        self.spec.remove_nodes(self.removed)
        if moment:
            self.start_moment(f"restart, {nodes}")

        params = self.build_params(conf)
        self.testbed.start(followers = nodes, leader=self.leaders[0], params=params,only_followers=True)

    def change_links(self, percentage, B, L, moment = True):
        pass
        self.used_topology.modify_links(percentage, B, L)
        self.spec = Spec(topology=self.used_topology)
        self.spec.remove_nodes(self.removed)
        if moment:
            self.start_moment(f"change links {percentage}% {B}MB {L}ms")
        spec = self.spec.spec
        self.testbed.set_links(spec)

    def restore_links(self, moment = True):
        self.used_topology = copy.deepcopy(self.base_topology)
        self.spec = Spec(topology=self.used_topology)
        self.spec.remove_nodes(self.removed)
        if moment:
            self.start_moment(f"restore links")
        spec = self.spec.spec
        self.testbed.set_links(spec)

    def isolate_group(self, boh, moment = True):
        pass
        if moment:
            self.start_moment(f"isolate group")
        # use cluster to break links in topology near cluster
        # apply links

    def start_experiment(self, conf):
        self.start_session("base and nodes")

        self.start_fogmon(conf)
        self.wait_stability()

        els = self.kill_nodes(leaders=len(self.leaders)//2,followers=len(self.followers)//4)
        self.wait_stability()
        self.restart_nodes(els, conf)
        self.wait_stability()

        els = self.kill_nodes(leaders=len(self.leaders)-1,followers=len(self.followers)//2)
        self.wait_stability()
        self.restart_nodes(els, conf)
        self.wait_stability()

        els = self.kill_nodes(leaders=len(self.leaders)-1,followers=0)
        self.wait_stability()
        self.restart_nodes(els, conf)
        self.wait_stability()

        self.stop_fogmon()
        
        
        self.start_session("links")

        self.start_fogmon(conf)
        self.wait_stability()

        links = self.change_links(5,100,500)
        self.wait_stability()
        self.restore_links(links)
        self.wait_stability()

        links = self.change_links(10,100,500)
        self.wait_stability()
        self.restore_links(links)
        self.wait_stability()

        # links = self.isolate_group(1)
        # self.wait_stability()
        # self.restore_links(links)
        # self.wait_stability()

        self.stop_fogmon()

if __name__ == "__main__":
    import sys
    import os
    if len(sys.argv)<=1:
        print("Usage: file.py param")
        print("param: load/start")
    
    if sys.argv[1] == "load":
        #path = input("insert testbed.zip path [e.g. ../file.zip]: ")
        try:
            os.remove("build")
        except:
            pass
        with ZipFile(sys.argv[2], 'r') as zipObj:
            # Extract all the contents of zip file in build directory
            zipObj.extractall("build")
        os.system("chmod 600 build/id_rsa")
    elif sys.argv[1] in  ["setup", "start", "stop", "test"]:
        #path = input("insert topology file path [e.g. ./topology]\nAlso make sure that topology file is the same used to generate the spec.xml for the build path loaded: ")
        topology = Topology.load(sys.argv[2])
        exp = Experimenter(topology)
        if sys.argv[1] == "setup":
            exp.setup()
        elif sys.argv[1] == "start":
            exp.start_experiment(configs["default"])
        elif sys.argv[1] == "stop":
            spec = Spec(topology=exp.base_topology).spec
            nodes = [node for node in spec["nodes"]]
            exp.testbed.stop(nodes)
        elif sys.argv[1] == "test":
            exp.sessions.append({"num": 20, "name": "base and", "session": 20, "moments": [],"version": 1})
            exp.get_roles()

    

