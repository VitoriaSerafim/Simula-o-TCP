#!/usr/bin/env python3
"""
Script para simular competição entre TCP Reno e TCP BBR no Mininet
Adaptado para: Dois fluxos TCP Reno competindo contra um fluxo TCP BBR.
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
        if self.name.startswith('h_reno'): # Para h_reno1, h_reno2
            self.cmd('sysctl -w net.ipv4.tcp_congestion_control=reno')
            info(f'{self.name}: TCP Reno configurado\n')
        elif self.name.startswith('h_bbr'): # Para h_bbr1 (apenas um)
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
    h_reno1 = net.addHost('h_reno1', ip='10.0.0.1/24')
    h_reno2 = net.addHost('h_reno2', ip='10.0.0.2/24')
    h_bbr1 = net.addHost('h_bbr1', ip='10.0.0.3/24') # Apenas um host BBR
    servidor = net.addHost('servidor', ip='10.0.0.4/24')
    
    # Adicionar switch
    s1 = net.addSwitch('s1')
    
    # Adicionar links com limitações de banda e latência para simular competição
    # Links dos hosts Reno para o switch (10Mbps, 5ms latência)
    net.addLink(h_reno1, s1, bw=10, delay='5ms', loss=0.1)
    net.addLink(h_reno2, s1, bw=10, delay='5ms', loss=0.1)
    
    # Link do host BBR para o switch (10Mbps, 5ms latência)  
    net.addLink(h_bbr1, s1, bw=10, delay='5ms', loss=0.1)
    
    # Link do servidor para o switch (20Mbps, 10ms latência - gargalo)
    net.addLink(servidor, s1, bw=20, delay='10ms', loss=0.2)
    
    # Iniciar rede
    net.start()
    
    # Verificar conectividade
    info("Testando conectividade\n")
    net.pingAll()
    
    return net, h_reno1, h_reno2, h_bbr1, servidor

def main():
    """Função principal do script"""
    
    # Configurar nível de log
    setLogLevel('info')
    
    print("=== SIMULAÇÃO TCP RENO vs BBR (2 Reno vs 1 BBR Fluxo) ===")
    print("Iniciando simulação...")
    
    # Criar arquivo de saída
    output_file = f"/tmp/tcp_comparison_2reno_1bbr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    # Criar diretório para servidor
    os.makedirs('/tmp/server_files', exist_ok=True)
    
    # Criar página HTML de teste
    create_test_html()
    
    # Inicializar cabeçalho do arquivo de resultados
    with open(output_file, 'w') as f:
        f.write("=== RELATÓRIO DE COMPARAÇÃO TCP RENO vs BBR (2 Reno vs 1 BBR Fluxo) ===\n")
        f.write(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 50 + "\n\n")
    
    try:
        # Criar topologia
        net, h_reno1, h_reno2, h_bbr1, servidor = create_topology()
        
        # Mostrar informações da rede
        info("Dump das conexões:\n")
        dumpNodeConnections(net.hosts)
        
        # Verificar configurações TCP
        info("Verificando configurações TCP:\n")
        hosts_to_check = [h_reno1, h_reno2, h_bbr1] # Apenas 3 hosts
        for host in hosts_to_check:
            tcp_config = host.cmd('sysctl net.ipv4.tcp_congestion_control')
            print(f"{host.name} TCP: {tcp_config.strip()}")
            with open(output_file, 'a') as f:
                f.write(f"{host.name} TCP Config: {tcp_config}")
        
        with open(output_file, 'a') as f:
            f.write("\n")
        
        # Iniciar servidor HTTP
        start_http_server(servidor)
        
        server_ip = servidor.IP()
        print(f"Servidor HTTP iniciado em: {server_ip}:8080")
        
        # Aguardar estabilização
        time.sleep(3)
        
        # Testes de latência inicial
        print("\n=== TESTE DE LATÊNCIA INICIAL ===")
        measure_latency(h_reno1, server_ip, "H_Reno1", output_file)
        measure_latency(h_reno2, server_ip, "H_Reno2", output_file)
        measure_latency(h_bbr1, server_ip, "H_BBR1", output_file)
        
        # Testes individuais de throughput com iperf3
        print("\n=== TESTES DE THROUGHPUT INDIVIDUAIS ===")
        run_iperf_test(h_reno1, servidor, "H_Reno1_Throughput", output_file)
        time.sleep(2)
        run_iperf_test(h_reno2, servidor, "H_Reno2_Throughput", output_file)
        time.sleep(2)
        run_iperf_test(h_bbr1, servidor, "H_BBR1_Throughput", output_file)
        time.sleep(2)
        
        # Teste simultâneo - a parte mais importante (2 Reno vs 1 BBR Fluxo)
        print("\n=== TESTE SIMULTÂNEO (COMPETIÇÃO: 2 Reno vs 1 BBR) ===")
        
        # Usar threads para execução simultânea
        def simultaneous_test(client_host, test_prefix):
            for i in range(3):  # Múltiplas requisições por host
                run_performance_test(client_host, server_ip, f"{test_prefix}_{i+1}", output_file)
                time.sleep(1) # Pequeno atraso entre as requisições do mesmo host
        
        # Iniciar monitoramento de estatísticas
        monitor_thread = threading.Thread(
            target=monitor_network_stats, 
            args=(servidor, "SERVER_MONITORING", output_file, 15) # Duração ajustada para 3 fluxos
        )
        monitor_thread.start()
        
        # Executar testes simultâneos para todos os hosts
        thread_reno1 = threading.Thread(target=simultaneous_test, args=(h_reno1, "H_Reno1_Simultaneous"))
        thread_reno2 = threading.Thread(target=simultaneous_test, args=(h_reno2, "H_Reno2_Simultaneous"))
        thread_bbr1 = threading.Thread(target=simultaneous_test, args=(h_bbr1, "H_BBR1_Simultaneous"))
        
        thread_reno1.start()
        thread_reno2.start()
        thread_bbr1.start()
        
        thread_reno1.join()
        thread_reno2.join()
        thread_bbr1.join()
        monitor_thread.join()
        
        # Teste de latência final
        print("\n=== TESTE DE LATÊNCIA FINAL ===")
        measure_latency(h_reno1, server_ip, "H_Reno1_Final", output_file)
        measure_latency(h_reno2, server_ip, "H_Reno2_Final", output_file)
        measure_latency(h_bbr1, server_ip, "H_BBR1_Final", output_file)
        
        # Coletar estatísticas finais
        print("\n=== ESTATÍSTICAS FINAIS ===")
        
        # Estatísticas TCP de cada host
        final_stats_content = "\n=== ESTATÍSTICAS FINAIS TCP ===\n"
        for host in hosts_to_check:
            stats = host.cmd('cat /proc/net/snmp | grep Tcp:')
            final_stats_content += f"{host.name}: {stats}"
        
        print(final_stats_content)
        
        with open(output_file, 'a') as f:
            f.write(final_stats_content)
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
