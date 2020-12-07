from fabric import Connection, Config
from fabric import task, SerialGroup
from enum import Enum
import json

class TestBeds(str, Enum):
   WALL1 = "urn:publicid:IDN+wall1.ilabt.iminds.be+authority+cm"
   WALL2 = "urn:publicid:IDN+wall2.ilabt.iminds.be+authority+cm"
   CITY = "urn:publicid:IDN+lab.cityofthings.eu+authority+cm"

class Ubuntu(str, Enum):
   WALL1 = "urn:publicid:IDN+wall1.ilabt.iminds.be+image+emulab-ops:UBUNTU18-64-STD"
   WALL2 = "urn:publicid:IDN+wall1.ilabt.iminds.be+image+emulab-ops:UBUNTU18-64-STD"
   CITY = "urn:publicid:IDN+lab.cityofthings.eu+image+emulab-ops:UBUNTU18-64-CoT-armgcc"

with open("spec.json", 'r') as rd:
   spec = json.load(rd)

user = "marcog"

enable_nat = ["wget -O - -nv https://www.wall2.ilabt.iminds.be/enable-nat.sh | sudo bash"]

docker = [
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
    #"newgrp docker"
    "sudo apt-get install screen"
]


def staging(ctx):
    if "CONNS" not in ctx:
        config = Config(
            overrides={
                'ssh_config_path': "./ssh-config",
                'load_ssh_configs': True,
            }
        )
        nodes = [n for (n,v) in spec["nodes"].items()]
        conns = SerialGroup(*nodes,
            config = config)
        ctx.CONNS = conns
    if "CONNS" not in ctx:
        print("still")

def getIpv6s(ctx):
    # resolve ips
    for conn in ctx.CONNS:
        out = conn.run("hostname -I")
        try:
            ipv6 = out.stdout.split(" ")[-2]
            spec["nodes"][conn.original_host]["ipv6"] = ipv6
        except:
            exit(1)

@task
def pingtest(ctx):
    staging(ctx)
    for conn in ctx.CONNS:
        conn.run('ping -c 3 8.8.8.8')

@task
def setupNetwork(ctx):
    staging(ctx)
    getIpv6s(ctx)
    for conn in ctx.CONNS:
        print(spec["nodes"][conn.original_host])
        conn.sudo(f"sed -i '/127.0.0.1\t{conn.original_host}/d' /etc/hosts")
        conn.run(f'sudo bash -c \'echo "127.0.0.1\t{conn.original_host}" >> /etc/hosts\'')
        if spec["nodes"][conn.original_host]["testbed"] == TestBeds.CITY.value:
            conn.run("sudo sudo ip link set dev enp2s0 mtu 1400")
        for l,v in spec["links"].items():
            if not v["same_testbed"] or v["testbed"] == TestBeds.CITY.value:
                n1 = v["interfaces"][0].split(":")[0]
                n2 = v["interfaces"][1].split(":")[0]
                found = False
                if n2 == conn.original_host:
                    othername = n1
                    grename = f"gre{othername}"
                    myipv6 = spec["nodes"][n2]["ipv6"]
                    otheripv6 = spec["nodes"][othername]["ipv6"]
                    myip = v["ips"][1]
                    otherip = v["ips"][0]
                    found = True
                if n1 == conn.original_host:
                    othername = n2
                    grename = f"gre{othername}"
                    myipv6 = spec["nodes"][n1]["ipv6"]
                    otheripv6 = spec["nodes"][othername]["ipv6"]
                    myip = v["ips"][0]
                    otherip = v["ips"][1]
                    found = True
                if found:
                    conn.run(f"sudo ip -6 link add name {grename} type ip6gre local {myipv6} remote {otheripv6} ttl 64")
                    conn.run(f"sudo ip link set up dev {grename}")
                    conn.run(f"sudo ip addr add {myip} peer {otherip} dev {grename}")
                    conn.run(f"sudo sudo ip link set dev {grename} mtu 1400")
                    conn.sudo(f"sed -i '/{otherip}/d' /etc/hosts")
                    conn.run(f'sudo bash -c \'echo "{otherip}\t{othername}" >> /etc/hosts\'')
                    if "capacity" in v or "latency" in v or "packet_loss" in v:
                        command = f"sudo tc qdisc add dev {grename} root netem "
                        if "latency" in v:
                            latency = v["latency"]
                            if not v["same_testbed"]:
                                latency -=3
                            else:
                                latency -=2
                            latency = latency//2
                            command+= f"delay {latency}ms "
                        if "capacity" in v:
                            capacity = v["capacity"]
                            command+= f"rate {capacity}kbit "
                        if "packet_loss" in v:
                            packet_loss = v["packet_loss"]
                            command+= f"loss random {packet_loss}% "
                        conn.run(command)
                        print(command)
        
@task
def removeNetwork(ctx):
    staging(ctx)
    for conn in ctx.CONNS:
        print(spec["nodes"][conn.original_host])
        conn.sudo(f"sed -i '/127.0.0.1\t{conn.original_host}/d' /etc/hosts")
        for l,v in spec["links"].items():
            n1 = v["interfaces"][0].split(":")[0]
            n2 = v["interfaces"][1].split(":")[0]
            found = False
            if n2 == conn.original_host:
                grename = f"gre{n1}"
                otherip = v["ips"][0]
                found = True
            if n1 == conn.original_host:
                grename = f"gre{n2}"
                otherip = v["ips"][1]
                found = True
            if found:
                try:
                    conn.run(f"sudo ip -6 link del dev {grename}")
                    conn.sudo(f"sed -i '/{otherip}/d' /etc/hosts")
                except:
                    pass

@task
def setupDocker(ctx):
    staging(ctx)
    for conn in ctx.CONNS:
        for n,v in spec["nodes"].items():
            if n == conn.original_host:
                file = "/tmp/script621f37ffa.sh"
                conn.run(f"> {file}")
                print(f"created {file}")
                conn.run(f"chmod +x {file}")
                if v["testbed"] != TestBeds.CITY.value:
                    for comm in enable_nat:
                        conn.run(f'echo \'{comm}\' >> {file}')
                for comm in docker:
                    conn.run(f'echo \'{comm}\' >> {file}')
                conn.run(f"screen -d -m -S docker bash -c '{file}'")

@task
def startFogmon(ctx):
    staging(ctx)
    leader = True
    for conn in ctx.CONNS:
        if leader:
            conn.run("screen -d -m -S fogmon bash -c 'sudo docker run -it --net=host diunipisocc/liscio-fogmon --leader'")
            leader = False
        else:
            conn.run("screen -d -m -S fogmon bash -c 'sudo docker run -it --net=host diunipisocc/liscio-fogmon -C node0'")
