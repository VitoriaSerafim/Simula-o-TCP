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
        # Cria um switch para o roteador
        switch = self.addSwitch('s0')
        
        # Cria os dois hosts
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')

        # Adiciona os links com as características apropriadas
        # Link do Host h1 para o roteador (conexão rápida)
        self.addLink(h1, switch, bw=args.bw_host, delay='%fms' % args.delay, max_queue_size=args.maxq)
        # Link do roteador para o Host h2 (gargalo)
        self.addLink(h2, switch, bw=args.bw_net, delay='%fms' % args.delay, max_queue_size=args.maxq)

def start_iperf(net):
    h1 = net.get('h1')
    h2 = net.get('h2')
    print("Starting iperf server...")
    # O parâmetro -w 16m garante que a janela TCP do receptor não seja o fator limitante
    server = h2.popen("iperf -s -w 16m")

    # Inicia o cliente iperf em h1 para criar um fluxo TCP de longa duração para h2
    print("Starting iperf client...")
    client_cmd = "iperf -c %s -t %d" % (h2.IP(), args.time + 5)
    h1.popen(client_cmd)

def start_qmon(iface, interval_sec=0.1, outfile="q.txt"):
    monitor = Process(target=monitor_qlen,
                      args=(iface, interval_sec, outfile))
    monitor.start()
    return monitor

def start_ping(net):
    h1 = net.get('h1')
    h2 = net.get('h2')
    outfile = "%s/ping.txt" % args.dir
    # Inicia um trem de pings de h1 para h2, com 10 amostras por segundo (-i 0.1)
    print("Starting ping...")
    ping_cmd = "ping -i 0.1 %s > %s" % (h2.IP(), outfile)
    h1.popen(ping_cmd, shell=True)

def start_webserver(net):
    h1 = net.get('h1')
    # Inicia um servidor web simples em h1
    print("Starting web server...")
    proc = h1.popen("python webserver.py", shell=True)
    sleep(1)
    return [proc]

def bufferbloat():
    if not os.path.exists(args.dir):
        os.makedirs(args.dir)
    os.system("sysctl -w net.ipv4.tcp_congestion_control=%s" % args.cong)
    topo = BBTopo()
    net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink)
    net.start()
    dumpNodeConnections(net.hosts)
    net.pingAll()

    # Inicia o monitoramento do tamanho da fila na interface de gargalo s0-eth2
    qmon = start_qmon(iface='s0-eth2',
                      outfile='%s/q.txt' % (args.dir))

    # Inicia os geradores de tráfego e servidores
    start_iperf(net)
    start_ping(net)
    web_procs = start_webserver(net)

    # Mede o tempo de download da página web
    h1 = net.get('h1')
    h2 = net.get('h2')
    fetch_times = []
    
    print("--- Starting experiment for %d seconds ---" % args.time)
    start_time = time()
    
    # Realiza 3 medições de download durante o experimento
    fetch_schedule = [args.time * 0.3, args.time * 0.5, args.time * 0.7]

    while True:
        now = time()
        delta = now - start_time
        if delta >= args.time:
            break

        if fetch_schedule and delta >= fetch_schedule[0]:
            fetch_schedule.pop(0)
            print("\n--- Fetching webpage, t=%.1f s ---" % delta)
            url = 'http://%s/index.html' % h1.IP()
            curl_cmd = 'curl -o /dev/null -s -w %%{time_total} %s' % url
            
            result = h2.popen(curl_cmd, shell=True, stdout=PIPE)
            # Lê o resultado, decodifica, remove espaços e troca vírgula por ponto
            fetch_time_str = result.stdout.read().decode().strip().replace(',', '.')
            if fetch_time_str:
                fetch_time = float(fetch_time_str)
                fetch_times.append(fetch_time)
                print("--- Fetch time: %.4f s ---\n" % fetch_time)
        
        sleep(1)

    # Calcula a média e o desvio padrão dos tempos de busca
    if fetch_times:
        avg_fetch = sum(fetch_times) / len(fetch_times)
        std_dev = math.sqrt(sum([(t - avg_fetch) ** 2 for t in fetch_times]) / len(fetch_times))
        
        print("\n--- Web Fetch Results ---")
        print("Average fetch time: %.4f s" % avg_fetch)
        print("Std dev fetch time: %.4f s" % std_dev)
        print("-------------------------\n")
        
        # Salva os resultados em um arquivo
        with open('%s/fetch_times.txt' % (args.dir), 'w') as f:
            f.write("Average: %.4f\n" % avg_fetch)
            f.write("Std Dev: %.4f\n" % std_dev)
            for t in fetch_times:
                f.write("%.4f\n" % t)
    
    # CLI(net) # Descomente para depuração manual

    # Finaliza todos os processos
    qmon.terminate()
    for proc in web_procs:
        proc.kill()
    Popen("killall -9 iperf ping", shell=True).wait()
    net.stop()
    Popen("pgrep -f webserver.py | xargs kill -9", shell=True).wait()

if __name__ == "__main__":
    bufferbloat()