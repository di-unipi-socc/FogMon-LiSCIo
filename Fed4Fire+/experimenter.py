#!/usr/bin/env python3
from os.path import expanduser
import requests
from spec import Spec
from testbed import Testbed
from topology import Topology, Node
import copy
from time import sleep
from datetime import datetime
from zipfile import ZipFile
import random
import json


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
        "-t": 60,
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
        "-t": 60,
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

    def connect(self, method, url, expected_status, tries=30, time=3, **params):
        for i in range(tries):
            try:
                if method == "GET":
                    r = requests.get(url, **params)
                    if r.status_code != expected_status:
                        raise Exception("connection error")
                elif method == "POST":
                    r = requests.post(url, **params)
                    if r.status_code != expected_status:
                        raise Exception("connection error")
                return r
            except KeyboardInterrupt:
                raise
            except:
                pass
            sleep(time)
        Exception("connection error")

    def testbed_try(self, method,tries=30, time=3, **param):
        for i in range(tries):
            try:
                val = method(**param)
                return val
            except KeyboardInterrupt:
                raise
            except:
                import traceback
                traceback.print_exc()
                pass
            print("retry")
            sleep(time)
        raise Exception("Testbed connection error")

    def clear_session(self, session):
        r = self.connect("GET",f"http://131.114.72.76:8248/testbed/{session}/remove",200)
        if r is None:
            raise Exception("connection error")

    def start_session(self, name):
        self.spec = Spec(topology=self.used_topology)
        self.spec.remove_nodes(self.removed)
        spec = self.spec.spec
        num = len(spec["nodes"])

        spec["id"] = len(self.sessions)
        r = self.connect("POST","http://131.114.72.76:8248/testbed",201, json=spec)
        session = r.json()["session"]
        self.sessions.append({"num": num, "name": name, "session": session, "moments": [],"version": 1})
        self.clear_session(session)
        print("session",self.sessions[-1])
        with open("../sessions.json","w") as wr:
            json.dump(self.sessions, wr)

    def start_moment(self, name):
        spec = self.spec.spec
        r = self.connect("POST",f"http://131.114.72.76:8248/testbed/{self.sessions[-1]['session']}",201, json=spec)
        moment = r.json()["moment"]
        self.sessions[-1]["moments"].append({"moment": moment, "name": name})
        print("session",self.sessions[-1]["moments"][-1])
        with open("../sessions.json","w") as wr:
            json.dump(self.sessions, wr)
        self.start_monitor()
    
    def start_monitor(self):
        spec = self.spec.spec
        nodes = [k for k in spec["nodes"]]
        self.testbed_try(self.testbed.start_monitor,nodes=nodes)

    def stop_monitor(self):
        spec = self.spec.spec
        nodes = [k for k in spec["nodes"]]
        self.testbed_try(self.testbed.stop_monitor,nodes=nodes)
        self.testbed_try(self.testbed.collect_monitor,nodes=nodes)
        files = {}
        for node in nodes:
            bmon = node+"-bmon.txt"
            psrecord = node+"-cpu.txt"
            try:
                files[bmon] = open(bmon,'rb')
                files[psrecord] = open(psrecord,'rb')
            except:
                pass
        print("sending monitored data")
        r = self.connect("POST",f"http://131.114.72.76:8248/testbed/{self.sessions[-1]['session']}/footprint",201, json=spec,files=files)

    def build_params(self, conf):
        conf["-s"] = self.sessions[-1]["session"]
        conf["-i"] = "131.114.72.76:8248"
        params = ""
        for param,val in conf.items():
            params += f"{param} {val} "
        return params

    def setup(self):
        spec = Spec(topology=self.base_topology).spec
        self.testbed_try(self.testbed.setup,spec=spec)

    def pull(self):
        spec = Spec(topology=self.base_topology).spec
        self.testbed_try(self.testbed.clean,nodes=[k for k in spec["nodes"]])
        self.testbed_try(self.testbed.pull,spec=spec)

    def start_fogmon(self, conf):
        spec = self.spec.spec
        followers = [k for k in spec["nodes"]]
        params = self.build_params(conf)
        self.testbed_try(self.testbed.start,followers=followers[1:],leader=followers[0],params=params)
        self.start_monitor()

    def stop_fogmon(self):
        try:
            self.stop_monitor()
        except:
            pass
        spec = self.spec.spec
        nodes = [k for k in spec["nodes"]]
        self.testbed_try(self.testbed.stop,nodes=nodes)
        with open("../sessions.json","w") as wr:
            json.dump(self.sessions, wr)

    def get_roles(self):
        r = self.connect("GET",f"http://131.114.72.76:8248/testbed/{self.sessions[-1]['session']}",200)
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
                r = self.connect("GET",f"http://131.114.72.76:8248/testbed/{self.sessions[-1]['session']}/accuracy",200,time=60)
                moments = r.json()["data"]
                moment = moments[-1]
                if "True" in moment["stable"]:# or "False (3)" in moment["stable"]:
                    stable = True
                    self.get_roles()
            except:
                pass
            time_delta = datetime.now() - start_time
            if time_delta.total_seconds() >= 60*60:
                break
        print(f"stable: {stable}", flush=True)
        if not stable:
            exit(1)
        return stable

    def kill_nodes(self, leaders, followers, moment = True):
        # leaders: number of leaders to kill
        # followers: number of followers to kill
        if moment:
            self.stop_monitor()
        nodes = []
        nodes += random.sample(self.leaders,leaders)
        nodes += random.sample(list(self.followers),followers)
        self.testbed_try(self.testbed.kill,nodes=nodes)
        self.removed += nodes
        self.spec.remove_nodes(self.removed)
        if moment:
            self.start_moment(f"kill {leaders} {followers}, {nodes}")
        return nodes

    def restart_nodes(self, nodes, conf, moment = True):
        if moment:
            self.stop_monitor()
        self.removed = [v for v in self.removed if v not in nodes]
        self.spec = Spec(topology=self.used_topology)
        self.spec.remove_nodes(self.removed)
        if moment:
            self.start_moment(f"restart, {nodes}")

        params = self.build_params(conf)
        self.testbed_try(self.testbed.start,followers = nodes, leader=self.leaders[0], params=params,only_followers=True)

    def change_links(self, percentage, B, L, moment = True):
        if moment:
            self.stop_monitor()
        self.used_topology.modify_links(percentage, B, L)
        self.spec = Spec(topology=self.used_topology)
        self.spec.remove_nodes(self.removed)
        if moment:
            self.start_moment(f"change links {percentage}% {B}MB {L}ms")
        spec = self.spec.spec
        self.testbed_try(self.testbed.set_links,spec=spec)

    def restore_links(self, moment = True):
        if moment:
            self.stop_monitor()
        self.used_topology = copy.deepcopy(self.base_topology)
        self.spec = Spec(topology=self.used_topology)
        self.spec.remove_nodes(self.removed)
        if moment:
            self.start_moment(f"restore links")
        spec = self.spec.spec
        self.testbed_try(self.testbed.set_links,spec=spec)

    def isolate_group(self, boh, moment = True):
        if moment:
            self.stop_monitor()
        pass
        if moment:
            self.start_moment(f"isolate group")
        # use cluster to break links in topology near cluster
        # apply links

    def start_experiment(self, conf):
        self.start_session("base and nodes")

        self.start_fogmon(conf)
        self.wait_stability()

        leaders = len(self.leaders)
        leaders = 2 #if leaders < 25 else 3 if leaders < 35 else 4
        followers = len(self.followers)//4
        els = self.kill_nodes(leaders=leaders,followers=followers)
        self.wait_stability()
        self.stop_fogmon()

        # self.restart_nodes(els, conf)
        # self.wait_stability()

        self.start_session("base and nodes")

        self.start_fogmon(conf)
        self.wait_stability()
        
        leaders = len(self.leaders)-1
        followers = len(self.followers)//2
        els = self.kill_nodes(leaders=leaders,followers=followers)
        self.wait_stability()
        self.stop_fogmon()

        # self.restart_nodes(els, conf)
        # self.wait_stability()

        self.start_session("base and nodes")

        self.start_fogmon(conf)
        self.wait_stability()

        leaders = len(self.leaders)-1
        els = self.kill_nodes(leaders=leaders,followers=0)
        self.wait_stability()
        self.stop_fogmon()
        
        # self.start_session("links")

        # self.start_fogmon(conf)
        # self.wait_stability()

        # self.change_links(5,100,500)
        # self.wait_stability()
        # self.restore_links()
        # self.wait_stability()

        # self.change_links(10,100,500)
        # self.wait_stability()
        # self.restore_links()
        # self.wait_stability()

        # links = self.isolate_group(1)
        # self.wait_stability()
        # self.restore_links(links)
        # self.wait_stability()

        # self.stop_fogmon()

    def test(self, conf):
        self.start_session("base and nodes")

        self.start_fogmon(conf)
        self.wait_stability()

        self.start_moment("No change (just fooprint")
        self.wait_stability()
        self.stop_fogmon()

if __name__ == "__main__":
    import sys
    import os
    if len(sys.argv)<=2:
        print("Usage: file.py param")
        print("param: toplogy_file/file.zip load/start")
    
    if sys.argv[2] == "load":
        #path = input("insert testbed.zip path [e.g. ../file.zip]: ")
        try:
            os.remove("build")
        except:
            pass
        with ZipFile(sys.argv[1], 'r') as zipObj:
            # Extract all the contents of zip file in build directory
            zipObj.extractall("build")
        os.system("chmod 600 build/id_rsa")
    elif sys.argv[2] in  ["setup", "network","pull", "start", "start2", "stop", "test"]:
        os.system("chmod 600 build/id_rsa")
        #path = input("insert topology file path [e.g. ./topology]\nAlso make sure that topology file is the same used to generate the spec.xml for the build path loaded: ")
        topology = Topology.load(sys.argv[1])
        exp = Experimenter(topology)
        if sys.argv[2] == "setup":
            exp.setup()
        elif sys.argv[2] == "network":
            exp.restore_links(moment=False)
        elif sys.argv[2] == "pull":
            exp.pull()
        elif sys.argv[2] == "start":
            exp.start_experiment(configs["default"])
        elif sys.argv[2] == "start2":
            with open("../sessions.json","r") as rd:
                exp.sessions = json.load(rd)
            exp.start_experiment(configs["default"])
        elif sys.argv[2] == "stop":
            with open("../sessions.json","r") as rd:
                exp.sessions = json.load(rd)
            exp.spec = Spec(topology=exp.base_topology)
            exp.stop_fogmon()
        elif sys.argv[2] == "test":
            with open("../sessions.json","r") as rd:
                exp.sessions = json.load(rd)
            exp.test(configs["default"])
            


