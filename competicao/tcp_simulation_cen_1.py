#!/usr/bin/env python3
"""
Script para simular competição entre TCP Reno e TCP BBR no Mininet
Autor: Script automático para análise de desempenho TCP
"""

import os
import time
import subprocess
import threading
from datetime import datetime
from mininet.net import Mininet
from mininet.node import Controller, OVSKernelSwitch, Host
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.util import dumpNodeConnections

class CustomHost(Host):
    """Host customizado para permitir configuração de TCP congestion control"""
    
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
    
    def config(self, **kwargs):
        super().config(**kwargs)
        # Configurar TCP congestion control baseado no nome do host
        if self.name == 'h1':
            # Configurar TCP Reno para h1
            self.cmd('sysctl -w net.ipv4.tcp_congestion_control=reno')
            info(f'{self.name}: TCP Reno configurado\n')
        elif self.name == 'h2':
            # Configurar TCP BBR para h2
            self.cmd('sysctl -w net.ipv4.tcp_congestion_control=bbr')
            info(f'{self.name}: TCP BBR configurado\n')

def create_test_html():
    """Cria uma página HTML de teste com conteúdo significativo"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Teste TCP Reno vs BBR</title>
    </head>
    <body>
        <h1>Página de Teste para Análise TCP</h1>
        <p>Este arquivo é usado para testar o desempenho entre TCP Reno e TCP BBR.</p>
        <!-- Adicionar conteúdo para aumentar o tamanho do arquivo -->
    """ + "        <p>Linha de padding para aumentar o tamanho do arquivo.</p>\n" * 1000 + """
    </body>
    </html>
    """
    
    with open('/tmp/test_page.html', 'w') as f:
        f.write(html_content)
    
    info("Página HTML de teste criada\n")

def start_http_server(host):
    """Inicia o servidor HTTP no host especificado"""
    # Copiar o arquivo HTML para o diretório do servidor
    host.cmd('cp /tmp/test_page.html /tmp/server_files/')
    
    # Iniciar servidor HTTP
    info(f"Iniciando servidor HTTP em {host.name}\n")
    host.cmd('cd /tmp/server_files && python3 -m http.server 8080 &')
    time.sleep(2)  # Aguardar o servidor inicializar

def run_performance_test(client_host, server_ip, test_name, output_file):
    """Executa teste de desempenho com curl e coleta métricas"""
    
    info(f"Iniciando teste para {test_name}\n")
    
    # Executar curl com métricas de tempo
    curl_cmd = f"""curl -w "
=== MÉTRICAS {test_name} ===
Tempo total: %{{time_total}}s
Tempo de conexão: %{{time_connect}}s
Tempo de transferência: %{{time_starttransfer}}s
Velocidade de download: %{{speed_download}} bytes/s
Tamanho baixado: %{{size_download}} bytes
Código HTTP: %{{http_code}}
" -o /tmp/{test_name}_download.html -s http://{server_ip}:8080/test_page.html"""
    
    # Executar comando e capturar saída
    result = client_host.cmd(curl_cmd)
    
    # Salvar resultados no arquivo
    with open(output_file, 'a') as f:
        f.write(f"\n{result}\n")
    
    print(result)
    
    return result

def measure_latency(client_host, server_ip, test_name, output_file):
    """Mede latência com ping"""
    
    info(f"Medindo latência para {test_name}\n")
    
    ping_cmd = f"ping -c 10 {server_ip}"
    result = client_host.cmd(ping_cmd)
    
    # Extrair estatísticas do ping
    lines = result.split('\n')
    for line in lines:
        if 'rtt' in line or 'round-trip' in line:
            latency_info = f"=== LATÊNCIA {test_name} ===\n{line}\n"
            
            with open(output_file, 'a') as f:
                f.write(latency_info)
            
            print(latency_info)
            break

def run_iperf_test(client_host, server_host, test_name, output_file):
    """Executa teste de throughput com iperf3"""
    
    info(f"Iniciando teste iperf3 para {test_name}\n")
    
    # Iniciar servidor iperf3 no servidor
    server_host.cmd('iperf3 -s -p 5001 -D')  # -D para daemon
    time.sleep(1)
    
    # Executar cliente iperf3
    iperf_cmd = f"iperf3 -c {server_host.IP()} -p 5001 -t 30"
    result = client_host.cmd(iperf_cmd)
    
    iperf_info = f"=== IPERF3 {test_name} ===\n{result}\n"
    
    with open(output_file, 'a') as f:
        f.write(iperf_info)
    
    print(iperf_info)
    
    # Parar servidor iperf3
    server_host.cmd('pkill iperf3')

def monitor_network_stats(host, test_name, output_file, duration=30):
    """Monitora estatísticas de rede durante o teste"""
    
    start_time = time.time()
    
    while time.time() - start_time < duration:
        # Coletar estatísticas TCP
        tcp_stats = host.cmd('cat /proc/net/snmp | grep Tcp:')
        
        # Coletar estatísticas de interface
        interface_stats = host.cmd('cat /proc/net/dev | grep eth0')
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        with open(output_file, 'a') as f:
            f.write(f"\n--- {test_name} Stats at {timestamp} ---\n")
            f.write(f"TCP Stats: {tcp_stats}")
            f.write(f"Interface Stats: {interface_stats}\n")
        
        time.sleep(5)

def create_topology():
    """Cria e configura a topologia de rede"""
    
    info("Criando topologia de rede\n")
    
    # Criar rede Mininet com links customizados
    net = Mininet(
        host=CustomHost,
        switch=OVSKernelSwitch,
        link=TCLink,
        controller=Controller
    )
    
    # Adicionar controller
    net.addController('c0')
    
    # Adicionar hosts
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    servidor = net.addHost('servidor', ip='10.0.0.3/24')
    
    # Adicionar switch
    s1 = net.addSwitch('s1')
    
    # Adicionar links com limitações de banda e latência para simular competição
    # Link do h1 para switch (10Mbps, 5ms latência)
    net.addLink(h1, s1, bw=10, delay='5ms', loss=0.1)
    
    # Link do h2 para switch (10Mbps, 5ms latência)  
    net.addLink(h2, s1, bw=10, delay='5ms', loss=0.1)
    
    # Link do servidor para switch (20Mbps, 10ms latência - gargalo)
    net.addLink(servidor, s1, bw=20, delay='10ms', loss=0.2)
    
    # Iniciar rede
    net.start()
    
    # Verificar conectividade
    info("Testando conectividade\n")
    net.pingAll()
    
    return net, h1, h2, servidor

def main():
    """Função principal do script"""
    
    # Configurar nível de log
    setLogLevel('info')
    
    print("=== SIMULAÇÃO TCP RENO vs BBR ===")
    print("Iniciando simulação...")
    
    # Criar arquivo de saída
    output_file = f"/tmp/tcp_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    # Criar diretório para servidor
    os.makedirs('/tmp/server_files', exist_ok=True)
    
    # Criar página HTML de teste
    create_test_html()
    
    # Inicializar cabeçalho do arquivo de resultados
    with open(output_file, 'w') as f:
        f.write("=== RELATÓRIO DE COMPARAÇÃO TCP RENO vs BBR ===\n")
        f.write(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 50 + "\n\n")
    
    try:
        # Criar topologia
        net, h1, h2, servidor = create_topology()
        
        # Mostrar informações da rede
        info("Dump das conexões:\n")
        dumpNodeConnections(net.hosts)
        
        # Verificar configurações TCP
        info("Verificando configurações TCP:\n")
        h1_tcp = h1.cmd('sysctl net.ipv4.tcp_congestion_control')
        h2_tcp = h2.cmd('sysctl net.ipv4.tcp_congestion_control')
        
        print(f"H1 TCP: {h1_tcp.strip()}")
        print(f"H2 TCP: {h2_tcp.strip()}")
        
        with open(output_file, 'a') as f:
            f.write(f"H1 TCP Config: {h1_tcp}")
            f.write(f"H2 TCP Config: {h2_tcp}\n")
        
        # Iniciar servidor HTTP
        start_http_server(servidor)
        
        server_ip = servidor.IP()
        print(f"Servidor HTTP iniciado em: {server_ip}:8080")
        
        # Aguardar estabilização
        time.sleep(3)
        
        # Testes de latência inicial
        print("\n=== TESTE DE LATÊNCIA INICIAL ===")
        measure_latency(h1, server_ip, "H1 (Reno)", output_file)
        measure_latency(h2, server_ip, "H2 (BBR)", output_file)
        
        # Testes individuais primeiro
        print("\n=== TESTES INDIVIDUAIS ===")
        run_performance_test(h1, server_ip, "H1_Individual", output_file)
        time.sleep(2)
        run_performance_test(h2, server_ip, "H2_Individual", output_file)
        time.sleep(2)
        
        # Testes de throughput com iperf3
        print("\n=== TESTES DE THROUGHPUT ===")
        run_iperf_test(h1, servidor, "H1_Throughput", output_file)
        time.sleep(2)
        run_iperf_test(h2, servidor, "H2_Throughput", output_file)
        time.sleep(2)
        
        # Teste simultâneo - a parte mais importante
        print("\n=== TESTE SIMULTÂNEO (COMPETIÇÃO) ===")
        
        # Usar threads para execução simultânea
        def simultaneous_test_h1():
            for i in range(3):  # Múltiplas requisições
                run_performance_test(h1, server_ip, f"H1_Simultaneous_{i+1}", output_file)
                time.sleep(1)
        
        def simultaneous_test_h2():
            for i in range(3):  # Múltiplas requisições
                run_performance_test(h2, server_ip, f"H2_Simultaneous_{i+1}", output_file)
                time.sleep(1)
        
        # Iniciar monitoramento de estatísticas
        monitor_thread = threading.Thread(
            target=monitor_network_stats, 
            args=(servidor, "SERVER_MONITORING", output_file, 15)
        )
        monitor_thread.start()
        
        # Executar testes simultâneos
        thread1 = threading.Thread(target=simultaneous_test_h1)
        thread2 = threading.Thread(target=simultaneous_test_h2)
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        monitor_thread.join()
        
        # Teste de latência final
        print("\n=== TESTE DE LATÊNCIA FINAL ===")
        measure_latency(h1, server_ip, "H1_Final", output_file)
        measure_latency(h2, server_ip, "H2_Final", output_file)
        
        # Coletar estatísticas finais
        print("\n=== ESTATÍSTICAS FINAIS ===")
        
        # Estatísticas TCP de cada host
        h1_stats = h1.cmd('cat /proc/net/snmp | grep Tcp:')
        h2_stats = h2.cmd('cat /proc/net/snmp | grep Tcp:')
        
        final_stats = f"""
=== ESTATÍSTICAS FINAIS TCP ===
H1 (Reno): {h1_stats}
H2 (BBR): {h2_stats}
"""
        
        print(final_stats)
        
        with open(output_file, 'a') as f:
            f.write(final_stats)
            f.write("\n=== FIM DO RELATÓRIO ===\n")
        
        print(f"\nResultados salvos em: {output_file}")
        
        # Opcional: abrir CLI para inspeção manual
        print("\nTeste concluído! Pressione Ctrl+C para sair ou digite 'CLI' para inspeção manual.")
        
        response = input("Deseja abrir o CLI do Mininet? (s/n): ").lower()
        if response == 's':
            CLI(net)
        
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuário")
    
    except Exception as e:
        print(f"Erro durante a execução: {e}")
        
    finally:
        # Limpeza
        if 'net' in locals():
            info("Parando rede\n")
            net.stop()
        
        # Limpar processos
        os.system('pkill -f "python3 -m http.server"')
        os.system('pkill -f "iperf3"')
        
        print("Simulação finalizada!")

if __name__ == '__main__':
    main()
