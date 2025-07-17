# bufferbloat.py
# Modificado para simular competição entre TCP Reno e TCP BBR

from mininet.topo import Topo
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.net import Mininet
from mininet.log import lg, info
from mininet.util import dumpNodeConnections
from mininet.cli import CLI
from subprocess import Popen, PIPE
from time import sleep, time
from multiprocessing import Process
from argparse import ArgumentParser

from monitor import monitor_qlen

import sys
import os
import math

parser = ArgumentParser(description="Bufferbloat tests")

parser.add_argument('--bw-host', '-B',
                    type=float,
                    help="Bandwidth of host links (Mb/s)",
                    default=1000)

parser.add_argument('--bw-net', '-b',
                    type=float,
                    help="Bandwidth of bottleneck (network) link (Mb/s)",
                    required=True)

parser.add_argument('--delay',
                    type=float,
                    help="Link propagation delay (ms)",
                    required=True)

parser.add_argument('--dir', '-d',
                    help="Directory to store outputs",
                    required=True)

parser.add_argument('--time', '-t',
                    help="Duration (sec) to run the experiment",
                    type=int,
                    default=10)

parser.add_argument('--maxq',
                    type=int,
                    help="Max buffer size of network interface in packets",
                    default=100)

parser.add_argument('--cong',
                    help="Congestion control algorithm to use",
                    default="reno")

args = parser.parse_args()

class BBTopo(Topo):
    "Simple topology for bufferbloat experiment."

    def build(self, n=2):
        h1 = self.addHost('h1', cpu=.5)
        h2 = self.addHost('h2', cpu=.5)
        switch = self.addSwitch('s0')

        self.addLink(h1, switch, bw=args.bw_host, delay='{}ms'.format(args.delay / 2))
        self.addLink(h2, switch, bw=args.bw_net, delay='{}ms'.format(args.delay / 2), max_queue_size=args.maxq)

def start_iperf(net):
    h1 = net.get('h1')
    h2 = net.get('h2')

    print("Iniciando servidor iperf3 em h2...")
    server = h2.popen("iperf3 -s -w 16m")
    sleep(1)

    print("Iniciando fluxo TCP Reno em h1...")
    reno_client_cmd_1 = "iperf3 -c %s -t %d --congestion reno -i 1 > %s/iperf_reno_flow1.txt" % (
        h2.IP(), args.time, args.dir
    )
    reno_client_1 = h1.popen(reno_client_cmd_1, shell=True)

    print("Iniciando fluxo TCP BBR em h1...")
    bbr_client_cmd_1 = "iperf3 -c %s -t %d --congestion bbr -i 1 > %s/iperf_bbr_flow1.txt" % (
        h2.IP(), args.time, args.dir
    )
    bbr_client_1 = h1.popen(bbr_client_cmd_1, shell=True)

def start_qmon(iface, interval_sec=0.1, outfile="q.txt"):
    monitor = Process(target=monitor_qlen,
                      args=(iface, interval_sec, outfile))
    monitor.start()
    return monitor

def start_ping(net):
    h1 = net.get('h1')
    h2 = net.get('h2')
    print("Iniciando trem de ping de h1 para h2...")
    ping_cmd = "ping -i 0.1 %s > %s/ping.txt" % (h2.IP(), args.dir)
    ping_process = h1.popen(ping_cmd, shell=True)
    return ping_process

def start_webserver(net):
    h1 = net.get('h1')
    print("Iniciando webserver em h1...")
    proc = h1.popen("python3 webserver.py", shell=True)
    sleep(1)
    return [proc]

def fetch_webpage(net):
    h2 = net.get('h2')
    web_server_ip = net.get('h1').IP()
    web_page_url = f"http://{web_server_ip}/index.html"
    curl_cmd = f"curl -o /dev/null -s -w %{{time_total}} {web_page_url}"
    result = h2.cmd(curl_cmd)
    try:
        fetch_time = float(result)
        return fetch_time
    except ValueError:
        print(f"Erro ao converter tempo de busca: {result}")
        return None

def bufferbloat():
    if not os.path.exists(args.dir):
        os.makedirs(args.dir)

    os.system("sysctl -w net.ipv4.tcp_congestion_control=%s" % args.cong)

    topo = BBTopo()
    net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink)
    net.start()

    dumpNodeConnections(net.hosts)
    net.pingAll()

    qmon = start_qmon(iface='s0-eth2', outfile='%s/q.txt' % (args.dir))
    start_iperf(net)
    ping_proc = start_ping(net)
    webserver_procs = start_webserver(net)

    fetch_times = []
    start_time = time()
    print(f"Experimento rodando por {args.time} segundos. Monitorando busca de webpage...")
    while True:
        for _ in range(3):
            fetch_time = fetch_webpage(net)
            if fetch_time is not None:
                fetch_times.append(fetch_time)
            sleep(0.1)
        
        sleep(5 - (3 * 0.1))
        now = time()
        delta = now - start_time
        if delta > args.time:
            break
        print("%.1fs left..." % (args.time - delta))

    if fetch_times:
        avg_fetch_time = sum(fetch_times) / len(fetch_times)
        if len(fetch_times) > 1:
            std_dev_fetch_time = math.sqrt(
                sum([(x - avg_fetch_time) ** 2 for x in fetch_times]) / len(fetch_times))
        else:
            std_dev_fetch_time = 0.0
        print(f"\nTempo médio de busca da webpage: {avg_fetch_time:.4f}s")
        print(f"Desvio padrão do tempo de busca da webpage: {std_dev_fetch_time:.4f}s")
    else:
        print("\nNenhum tempo de busca de webpage coletado.")

    qmon.terminate()
    ping_proc.terminate()
    net.stop()
    Popen("pgrep -f webserver.py | xargs kill -9", shell=True).wait()
    Popen("pgrep -f iperf3 | xargs kill -9", shell=True).wait()

if __name__ == "__main__":
    bufferbloat()
