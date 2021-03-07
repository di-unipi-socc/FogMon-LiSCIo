from fabric import Connection, Config
from fabric import task, SerialGroup, ThreadingGroup
from time import sleep
from enum import Enum
import threading
import os

class TestBeds(str, Enum):
    WALL1 = "urn:publicid:IDN+wall1.ilabt.iminds.be+authority+cm"
    WALL2 = "urn:publicid:IDN+wall2.ilabt.iminds.be+authority+cm"
    CITY = "urn:publicid:IDN+lab.cityofthings.eu+authority+cm"

class Ubuntu(str, Enum):
    WALL1 = "urn:publicid:IDN+wall1.ilabt.iminds.be+image+emulab-ops:UBUNTU18-64-STD"
    WALL2 = "urn:publicid:IDN+wall1.ilabt.iminds.be+image+emulab-ops:UBUNTU18-64-STD"
    CITY = "urn:publicid:IDN+lab.cityofthings.eu+image+emulab-ops:UBUNTU18-64-CoT-armgcc"

enable_nat = ["wget -O - -nv https://www.wall2.ilabt.iminds.be/enable-nat.sh | sudo bash"]

user = "marcog"

fogmon_images = [
    "diunipisocc/liscio-fogmon:test",
    "diunipisocc/liscio-fogmon:test2",
    "diunipisocc/liscio-fogmon:valgrind"
]

docker_script = [
    'sudo service ntp stop',
    'sudo ntpdate pool.ntp.org',
    "sudo apt-get -y update",
    "sudo DEBIAN_FRONTEND=noninteractive apt-get -y install apt-transport-https ca-certificates curl gnupg-agent software-properties-common",
    "sudo apt-get remove docker docker-engine docker.io containerd runc",
    "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -",
    'sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"',
    "sudo apt-get update",
    "sudo apt-get install -y docker-ce docker-ce-cli containerd.io",
    f"sudo usermod -aG docker {user}",
    "sudo apt-get install -y bmon",
]

monitor_script = [
    "bmon -r 1 -o format:fmt='\\$(element:name) \\$(attr:rxrate:bytes) \\$(attr:txrate:bytes)\\n' -p \\$(ip route | grep default | sed -e 's/^.*dev.//' -e 's/.proto.*//') > bmon.log &",
    "P1=\\$!",
    "sudo docker stats --format '{{.Container}}\\t{{.CPUPerc}}\\t{{.MemUsage}}' > test.log &",
    "P2=\\$!",
    "wait \\$P1 \\$P2",
    "echo 'Done'"
]

class Testbed:

    def __init__(self, path = "build"):
        self.config = Config(
            overrides={
                'ssh_config_path': f"./{path}/ssh-config",
                'load_ssh_configs': True,
            }
        )
        os.chdir(path)

    def exec_script(self, name, lines, nodes):
        conns = ThreadingGroup(*nodes,
            config = self.config)
        file = f"/tmp/script-{name}.sh"
        conns.run(f"> {file}", hide=True)
        conns.run(f"chmod +x {file}", hide=True)
        script = ""
        for line in lines:
            script += f"sudo {line}\n"
        
        script = script.replace("'","\\'")
        conns.run(f'echo $\'{script}\' > {file}', hide=True)
        conns.run(f"screen -d -m -S {name} bash -c '{file}'", hide=True)

    def exec_scripts(self, name, scripts: dict):
        threads = []
        for node in scripts:
            x = threading.Thread(target=self.exec_script, args=(name,scripts[node], [node]))
            threads.append(x)
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    def get_file(self, node, src_name, dst_name):
        conn = Connection(node,
            config = self.config)
        conn.get(src_name, dst_name)

    def get_files(self, nodes: list, src_name: str, dst_name: str):
        threads = []
        for node in nodes:
            x = threading.Thread(target=self.get_file, args=(node,src_name, f"{node}-{dst_name}"))
            threads.append(x)
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    def wait_script(self, name, nodes, retry = 0, timeout = 1):
        conns = ThreadingGroup(*nodes,
            config = self.config)
        i = 0
        while True:
            results = conns.run(f"screen -S {name} -Q select . > /dev/null 2>&1 ; echo $?", hide=True)
            if len([r for r in results if int(results[r].stdout) != 1]) == 0:
                break
            print(f"waiting {name}:",len([r.original_host for r in results if int(results[r].stdout) != 1]),"\r",end="")
            sleep(timeout)
            if i>retry and retry != 0 :
                return False
            i += 1
        return True

    def getIpv6s(self, spec):
        # resolve ips
        nodes = [node for node in spec["nodes"]]
        conns = ThreadingGroup(*nodes,
            config = self.config)
        
        results = conns.run("hostname -I", hide=True)
        for r in results:
            try:
                ipv6 = results[r].stdout.split(" ")[-2]
                spec["nodes"][r.original_host]["ipv6"] = ipv6
            except:
                exit(1)

    def generate_init_network_scripts(self, spec):
        scripts = {}
        for node in spec["nodes"]:
            comms = []
            comms.append(f"sed -i -E 's/([a-z0-9-]+) ([a-zA-Z0-9-]+) ([a-zA-Z0-9-]+)$/\\3 \\1 \\2/' /etc/hosts")
            comms.append(f"sed -i '/127.0.0.1\t{node}/d' /etc/hosts")
            comms.append(f'bash -c \'echo "127.0.0.1\t{node}" >> /etc/hosts\'')
            if spec["nodes"][node]["testbed"] != TestBeds.CITY.value:
                for comm in enable_nat:
                    comms.append(comm)
            for l,v in spec["links"].items():
                n1 = v["interfaces"][0].split(":")[0]
                n2 = v["interfaces"][1].split(":")[0]
                found = False
                if n2 == node:
                    othername = n1
                    otherip = v["ips"][0]
                    found = True
                if n1 == node:
                    othername = n2
                    otherip = v["ips"][1]
                    found = True
                if found:
                    comms.append(f"sed -i '/{otherip}/d' /etc/hosts")
                    comms.append(f'bash -c \'echo "{otherip}\t{othername}" >> /etc/hosts\'')
            scripts[node] = comms
        return scripts
    
    def generate_network_scripts(self, spec):
        self.getIpv6s(spec)
        scripts = {}
        for node in spec["nodes"]:
            comms = []
            for l,v in spec["links"].items():
                n1 = v["interfaces"][0].split(":")[0]
                n2 = v["interfaces"][1].split(":")[0]
                found = False
                if n2 == node:
                    othername = n1
                    myip = v["ips"][1]
                    otherip = v["ips"][0]
                    found = True
                if n1 == node:
                    othername = n2
                    myip = v["ips"][0]
                    otherip = v["ips"][1]
                    found = True
                grename = f"gre{othername}"
                myipv6 = spec["nodes"][node]["ipv6"]
                otheripv6 = spec["nodes"][othername]["ipv6"]
                if found:
                    comms.append(f"ip -6 link del dev {grename} ; echo $?")
                    comms.append(f"ip -6 link add name {grename} type ip6gre local {myipv6} remote {otheripv6} ttl 64")
                    comms.append(f"ip link set up dev {grename}")
                    comms.append(f"ip addr add {myip} peer {otherip} dev {grename}")
                    comms.append(f"ip link set dev {grename} mtu 1400")
                    if "capacity" in v or "latency" in v or "packet_loss" in v:
                        command = f"tc qdisc add dev {grename} root netem "
                        if "latency" in v:
                            latency = v["latency"]
                            if not v["same_testbed"]:
                                latency -=4
                            elif v["testbed"] == TestBeds.CITY.value:
                                latency -=3
                            latency = latency//2
                            command+= f"delay {latency}ms "
                        if "capacity" in v:
                            capacity = v["capacity"]
                            command+= f"rate {capacity}kbit "
                        if "packet_loss" in v:
                            packet_loss = v["packet_loss"]
                            command+= f"loss random {packet_loss}% "
                        comms.append(command)
            scripts[node] = comms
        return scripts

    def setup(self, spec):
        nodes = [node for node in spec["nodes"]]
        # setup network
        scripts = self.generate_init_network_scripts(spec)
        self.exec_scripts("network-init",scripts)
        self.wait_script("network-init", nodes)

        scripts = self.generate_network_scripts(spec)
        self.exec_scripts("network",scripts)
        self.wait_script("network", nodes)

        # setup docker
        self.exec_script("docker", docker_script, nodes)
        self.wait_script("docker", nodes,timeout=20)

        # pull fogmon
        self.exec_script("pull", [f"sudo docker pull {fogmon_images[0]}"], nodes)
        self.wait_script("pull", nodes)

    def pull(self, spec):
        nodes = [node for node in spec["nodes"]]
        self.exec_script("pull", [f"sudo docker pull {fogmon_images[0]}"], nodes)
        self.wait_script("pull", nodes)

    def start(self, followers, leader, params, image=fogmon_images[0], only_followers = False):
        conn = Connection(leader, config=self.config)
        conns = ThreadingGroup(*followers,
            config = self.config)

        if not only_followers:
            conn.run(f"screen -d -m -S fogmon bash -c 'sudo docker run -it --net=host {image} --leader {params} | tee log.txt'")
        conns.run(f"screen -d -m -S fogmon bash -c 'sudo docker run -it --net=host {image} -C {leader} {params} | tee log.txt'")

    def stop(self, nodes):
        conns = ThreadingGroup(*nodes,
            config = self.config)
        conns.run("screen -S fogmon -X stuff '0'`echo -ne '\015'` | sudo docker ps")
        for i in range(30):
            results = conns.run("screen -S fogmon -Q select . > /dev/null 2>&1 ; echo $?", hide=True)
            if len([r for r in results if int(results[r].stdout) != 1]) == 0:
                return True
            print("Retry...",end=" ",flush=True)
            sleep(1)
        print("Not terminated")
        return False

    def kill(self, nodes):
        conns = ThreadingGroup(*nodes,
            config = self.config)
        conns.run("sudo docker kill $(docker ps -q) | sudo docker ps")
        for i in range(30):
            results = conns.run("screen -S fogmon -Q select . > /dev/null 2>&1 ; echo $?", hide=True)
            if len([r for r in results if int(results[r].stdout) != 1]) == 0:
                return True
            print("Retry...",end=" ",flush=True)
            sleep(1)
        print("Not terminated")
        return False

    def set_links(self, spec):
        nodes = [node for node in spec["nodes"]]
        scripts = self.generate_network_scripts(spec)
        self.exec_scripts("network",scripts)
        self.wait_script("network", nodes)

    def start_monitor(self, nodes):
        scripts = {node:monitor_script for node in nodes}
        self.exec_scripts("monitor",scripts)
    
    def collect_monitor(self, nodes):
        self.get_files(nodes, "test.log", "cpu.txt")
        self.get_files(nodes, "bmon.log", "bmon.txt")

    def stop_monitor(self, nodes):
        conns = ThreadingGroup(*nodes,
            config = self.config)
        conns.run("screen -S monitor -X stuff '0'`echo -ne $'\cc'` | screen -list | ps ax | grep 'bmon'")
        for i in range(30):
            results = conns.run("screen -S monitor -Q select . > /dev/null 2>&1 ; echo $?", hide=True)
            if len([r for r in results if int(results[r].stdout) != 1]) == 0:
                return True
            print("Retry...",end=" ",flush=True)
            sleep(1)
        print("Not terminated")
        return False
        