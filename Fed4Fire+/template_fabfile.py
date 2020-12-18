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

user = "marcog"

enable_nat = ["wget -O - -nv https://www.wall2.ilabt.iminds.be/enable-nat.sh | sudo bash"]

image = "diunipisocc/liscio-fogmon:test"

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
    f"sudo docker pull {image}"
]

vbox = [
    'sudo wget -q https://www.virtualbox.org/download/oracle_vbox_2016.asc -O- | sudo apt-key add -',
    'echo "deb [arch=amd64] https://download.virtualbox.org/virtualbox/debian focal contrib" | sudo tee /etc/apt/sources.list.d/virtualbox.list',
    'sudo apt update',
    'sudo apt-get install --yes virtualbox',
    f'sudo usermod -aG vboxusers {user}',
    'echo virtualbox-ext-pack virtualbox-ext-pack/license select true | sudo debconf-set-selections',
    'sudo apt install -y virtualbox-ext-pack',
    'VBoxManage setproperty vrdeextpack "Oracle VM VirtualBox Extension Pack"',
    f'sudo chown {user}:vboxusers /mnt -R',
    'sudo apt install -y virtualbox-guest-additions-iso',
    #'wget -O /mnt/ubuntu-18.04.5-live-server-amd64.iso https://releases.ubuntu.com/18.04.5/ubuntu-18.04.5-live-server-amd64.iso'
    
    #'wget -O /mnt/Ubuntu_18.04.7z https://sourceforge.net/projects/osboxes/files/v/vb/59-U-u-svr/18.04/18.04.3/S18.04.3VB-64bit.7z/download',
    #'sudo apt install -y p7zip-full',
    #'7z e /mnt/Ubuntu_18.04.7z -o/mnt',
    #'rm /mnt/64bit -r',
    #'mv "/mnt/Ubuntu Server 18.04.3 (64bit).vdi" /mnt/Ubuntu_18.04.vdi',
]

startvbox = [
    'vboxmanage createvm --ostype Ubuntu_64 --basefolder "/mnt/virtualbox" --register --name "%s"',
    #'cp /mnt/Ubuntu_18.04.vdi /mnt/virtualbox/%s/Ubuntu_18.04.vdi',
    'vboxmanage modifyvm "%s" --memory 1024 --nic2 nat --vrde on --vrdeport 33890',
    'vboxmanage modifyvm "%s" --nic1 bridged --bridgeadapter1 enp1s0f0',
    'VBoxManage modifyvm  "%s" --natpf1 "guestssh,tcp,,2222,,22"',
    'vboxmanage createhd --filename "/mnt/virtualbox/%s/%s.vmdk" --format VMDK --size 16384 --variant stream',
    'vboxmanage storagectl "%s" --name "SATA" --add sata',
    'vboxmanage storageattach "%s" --storagectl SATA --port 0 --type hdd --medium "/mnt/virtualbox/%s/%s.vdi"',
    #'vboxmanage storageattach "%s" --storagectl SATA --port 0 --type hdd --medium "/mnt/virtualbox/%s/Ubuntu_18.04.vdi"',
    #'vboxmanage storageattach "%s" --storagectl SATA --port 15 --type dvddrive --medium /usr/share/virtualbox/VBoxGuestAdditions.iso',
    #'vboxmanage storageattach "%s" --storagectl SATA --port 15 --type dvddrive --medium /mnt/ubuntu-18.04.5-live-server-amd64.iso',
    'vboxmanage startvm "%s" --type headless',
    'VBoxManage controlvm "%s" poweroff',

]
# <emulab:blockstore name="bs1" size="60GB" mountpoint="/mnt" class="local"/>

# rdesktop localhost:33890

# sudo dhclient -r
# sudo dhclient
# sudo apt install openssh-server
# sudo apt install -y build-essential gcc make perl dkms
# sudo mount /dev/cdrom /mnt
# sudo /mnt/VBoxLinuxAdditions.run
# reboot

# VBoxManage guestproperty get <vmname> "/VirtualBox/GuestInfo/Net/0/V4/IP"
# vboxmanage clonehd file.vmdk clone.vmdk

# everyboot
# wget -O - -nv https://www.wall2.ilabt.iminds.be/enable-nat.sh | sudo bash



def staging(ctx):
    if "SPEC" not in ctx:
        with open("spec.json", 'r') as rd:
            ctx.SPEC = json.load(rd)
    spec = ctx.SPEC
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

def getIpv6s(ctx):
    # resolve ips
    spec = ctx.SPEC
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
    spec = ctx.SPEC
    for conn in ctx.CONNS:
        print(spec["nodes"][conn.original_host])
        conn.sudo(f"sed -i -E 's/([a-z0-9-]+) ([a-zA-Z0-9-]+) ([a-zA-Z0-9-]+)$/\\3 \\1 \\2/' /etc/hosts")
        conn.sudo(f"sed -i '/127.0.0.1\t{conn.original_host}/d' /etc/hosts")
        conn.run(f'sudo bash -c \'echo "127.0.0.1\t{conn.original_host}" >> /etc/hosts\'')
        if spec["nodes"][conn.original_host]["testbed"] != TestBeds.CITY.value:
            for comm in enable_nat:
                conn.run(comm)
        if spec["nodes"][conn.original_host]["testbed"] == TestBeds.CITY.value:
            conn.run("sudo sudo ip link set dev enp2s0 mtu 1400")
        for l,v in spec["links"].items():
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
            if not v["same_testbed"] or v["testbed"] == TestBeds.CITY.value:
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
    spec = ctx.SPEC
    for conn in ctx.CONNS:
        print(spec["nodes"][conn.original_host])
        conn.sudo(f"sed -i '/127.0.0.1\t{conn.original_host}/d' /etc/hosts")
        conn.sudo(f"sed -i -E 's/([a-z0-9-]+) ([a-zA-Z0-9-]+) ([a-zA-Z0-9-]+)$/\\3 \\1 \\2/' /etc/hosts")
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
    spec = ctx.SPEC
    for conn in ctx.CONNS:
        for n,v in spec["nodes"].items():
            if n == conn.original_host:
                file = "/tmp/script621f37ffa.sh"
                conn.run(f"> {file}")
                print(f"created {file}")
                conn.run(f"chmod +x {file}")
                for comm in docker:
                    conn.run(f'echo \'{comm}\' >> {file}')
                conn.run(f"screen -d -m -S docker bash -c '{file}'")

@task
def setupVbox(ctx):
    staging(ctx)
    spec = ctx.SPEC
    for conn in ctx.CONNS:
        for n,v in spec["nodes"].items():
            if n == conn.original_host:
                file = "/tmp/script6df5dfa.sh"
                conn.run(f"> {file}")
                print(f"created {file}")
                conn.run(f"chmod +x {file}")
                for comm in vbox:
                    conn.run(f'echo \'{comm}\' >> {file}')
                conn.run(f"screen -d -m -S vbox bash -c '{file}'")

@task
def pullFogmon(ctx):
    staging(ctx)
    for conn in ctx.CONNS:
        conn.run(f"screen -d -m -S fogmon bash -c 'sudo docker pull {image}'")


@task
def startFogmon(ctx):
    staging(ctx)
    leader = None
    for conn in ctx.CONNS:
        if leader is None:
            conn.run(f"screen -d -m -S fogmon bash -c 'sudo docker run -it --net=host {image} --leader'")
            leader = conn.original_host
        else:
            conn.run(f"screen -d -m -S fogmon bash -c 'sudo docker run -it --net=host {image} -C {leader}'")
