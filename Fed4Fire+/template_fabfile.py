from fabric import Connection, Config
from fabric import task, SerialGroup
import os

user = "marcog"

enable_nat = ["wget -O - -nv https://www.wall2.ilabt.iminds.be/enable-nat.sh | sudo bash"]

docker = [
   "sudo apt -y update",
   "sudo DEBIAN_FRONTEND=noninteractive apt -y install apt-transport-https ca-certificates curl gnupg-agent software-properties-common",
   "sudo apt remove docker docker-engine docker.io containerd runc",
   "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -",
   'sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"',
   "sudo apt update",
   "sudo apt install -y docker-ce docker-ce-cli containerd.io",
   f"sudo usermod -aG docker {user}",
   "newgrp docker"
]

def staging(ctx):
    if "CONNS" not in ctx:
        config = Config(
            overrides={
                'ssh_config_path': "./ssh-config",
                'load_ssh_configs': True,
            }
        )
        conns = SerialGroup(*["node0","node1"],
            config = config)
        ctx.CONNS = conns
    if "CONNS" not in ctx:
        print("still")

@task
def pingtest(ctx):
    staging(ctx)
    for conn in ctx.CONNS:
        conn.run('ping -c 3 8.8.8.8')

@task
def setup(ctx):
    staging(ctx)
    for conn in ctx.CONNS:
        for comm in enable_nat:
            conn.run(comm)
        for comm in docker:
            print(comm)
            conn.run(comm)