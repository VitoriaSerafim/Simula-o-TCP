import re
import matplotlib.pyplot as plt
import numpy as np

# Define um estilo visual para os gráficos
plt.style.use('seaborn-v0_8-whitegrid')

def normalize_to_mbits(value_str, unit_str):
    """Converte um valor de Kbits ou bits para Mbits."""
    value = float(value_str)
    unit = unit_str.upper()
    if unit == 'K':
        return value / 1000.0
    elif unit == '': # bits/sec
        return value / 1000000.0
    return value # Mbits/sec

def parse_iperf_data(content, host_id):
    """
    Extrai dados de vazão e retransmissão para um host específico.
    """
    section_pattern = re.compile(f"=== IPERF3 {host_id}_Throughput ===(.*?)iperf Done.", re.DOTALL)
    section_match = section_pattern.search(content)

    if not section_match:
        print(f"Aviso: Seção iperf para {host_id} não encontrada.")
        return {'times': [], 'bitrates': [], 'retrs': []}

    section_content = section_match.group(1)

    # Regex aprimorada para capturar Mbits, Kbits ou bits/sec
    line_pattern = re.compile(r"\[\s*\d+\]\s+[\d\.]+-([\d\.]+)\s+sec.*\s+([\d\.]+)\s+([KM]?)bits/sec\s+(\d+)")

    times, bitrates, retrs = [], [], []
    for line in section_content.splitlines():
        match = line_pattern.search(line)
        if match:
            times.append(float(match.group(1)))
            # Normaliza a vazão para Mbits/sec
            bitrate = normalize_to_mbits(match.group(2), match.group(3))
            bitrates.append(bitrate)
            retrs.append(int(match.group(4)))

    return {'times': times, 'bitrates': bitrates, 'retrs': retrs}

def parse_summary_stats(content, host_id):
    """
    Extrai a vazão média final e o total de retransmissões para um host específico.
    """
    section_pattern = re.compile(f"=== IPERF3 {host_id}_Throughput ===(.*?)iperf Done.", re.DOTALL)
    section_match = section_pattern.search(content)
    if not section_match:
        return None

    summary_pattern = re.compile(r"\[\s+\d+\]\s+0\.00-[\d\.]+\s+sec.*?([\d\.]+)\s+Mbits/sec\s+(\d+)\s+sender")
    match = summary_pattern.search(section_match.group(1))

    if match:
        avg_bitrate = float(match.group(1))
        total_retr = int(match.group(2))
        return {'avg_bitrate': avg_bitrate, 'total_retr': total_retr}
    
    print(f"Aviso: Estatísticas de resumo para {host_id} não encontradas.")
    return {'avg_bitrate': 0, 'total_retr': 0}

def parse_latency(content, host_id, stage):
    """
    Extrai a latência média (RTT) para um host específico.
    """
    if stage == 'Final':
        pattern_str = f"=== LATÊNCIA {host_id}_Final ===\s+rtt min/avg/max/mdev = .*?/([\d\.]+)/.*/.*ms"
    else:
        pattern_str = f"=== LATÊNCIA {host_id} ===\s+rtt min/avg/max/mdev = .*?/([\d\.]+)/.*/.*ms"
    
    pattern = re.compile(pattern_str)
    match = pattern.search(content)

    if match:
        return float(match.group(1))
    
    print(f"Aviso: Latência para {host_id} ({stage}) não encontrada.")
    return 0

def combine_protocol_data(data_list):
    """
    Combina dados de múltiplos hosts do mesmo protocolo.
    Retorna a média das vazões e soma das retransmissões.
    """
    if not data_list or not any(data['times'] for data in data_list):
        return {'times': [], 'bitrates': [], 'retrs': []}
    
    # Encontra o maior número de intervalos de tempo
    max_len = max(len(data['times']) for data in data_list if data['times'])
    
    # Inicializa listas para os dados combinados
    combined_times = []
    combined_bitrates = []
    combined_retrs = []
    
    for i in range(max_len):
        time_values = []
        bitrate_values = []
        retr_values = []
        
        for data in data_list:
            if i < len(data['times']):
                time_values.append(data['times'][i])
                bitrate_values.append(data['bitrates'][i])
                retr_values.append(data['retrs'][i])
        
        if time_values:
            combined_times.append(np.mean(time_values))
            combined_bitrates.append(np.mean(bitrate_values))  # Média da vazão
            combined_retrs.append(sum(retr_values))  # Soma das retransmissões
    
    return {'times': combined_times, 'bitrates': combined_bitrates, 'retrs': combined_retrs}

def plot_throughput_over_time(reno_data, bbr_data):
    """Gera o gráfico de vazão ao longo do tempo para cenário 3."""
    plt.figure(figsize=(12, 7))
    plt.plot(reno_data['times'], reno_data['bitrates'], marker='x', linestyle='--', 
             label='TCP Reno (média 2 hosts)', color='red', linewidth=2)
    plt.plot(bbr_data['times'], bbr_data['bitrates'], marker='o', linestyle='-', 
             markersize=5, label='TCP BBR (1 host)', color='blue', linewidth=2)
    plt.title('Vazão TCP Reno (2 hosts) vs. BBR (1 host) ao Longo do Tempo (Cenário 3)', fontsize=16)
    plt.xlabel('Tempo (segundos)', fontsize=12)
    plt.ylabel('Vazão (Mbits/segundo)', fontsize=12)
    plt.legend()
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.tight_layout()
    plt.savefig('grafico_vazao_tempo_cen3.png', dpi=300, bbox_inches='tight')
    print("Gráfico 'grafico_vazao_tempo_cen3.png' salvo.")

def plot_retransmissions_over_time(reno_data, bbr_data):
    """
    Gera o gráfico de retransmissões ao longo do tempo para cenário 3.
    """
    plt.figure(figsize=(12, 7))
    
    # Garante que ambas as listas tenham o mesmo tamanho para plotagem
    max_len = max(len(reno_data['times']), len(bbr_data['times']))
    
    reno_retrs = reno_data['retrs'] + [0] * (max_len - len(reno_data['retrs']))
    bbr_retrs = bbr_data['retrs'] + [0] * (max_len - len(bbr_data['retrs']))
    
    reno_times = reno_data['times'] + [0] * (max_len - len(reno_data['times']))
    bbr_times = bbr_data['times'] + [0] * (max_len - len(bbr_data['times']))

    bar_width = 0.35
    r1 = np.arange(max_len)
    r2 = [x + bar_width for x in r1]
    
    xtick_labels = reno_times if len(reno_times) >= len(bbr_times) else bbr_times

    plt.bar(r1, reno_retrs, color='red', width=bar_width, edgecolor='grey', 
            label='TCP Reno (soma 2 hosts)', alpha=0.8)
    plt.bar(r2, bbr_retrs, color='blue', width=bar_width, edgecolor='grey', 
            label='TCP BBR (1 host)', alpha=0.8)

    plt.title('Retransmissões por Segundo: Reno (2 hosts) vs. BBR (1 host) - Cenário 3', fontsize=16)
    plt.xlabel('Tempo (segundos)', fontsize=12)
    plt.ylabel('Número de Retransmissões', fontsize=12)
    plt.xticks([r + bar_width/2 for r in range(max_len)], [int(t) for t in xtick_labels], rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.savefig('grafico_retransmissoes_tempo_cen3.png', dpi=300, bbox_inches='tight')
    print("Gráfico 'grafico_retransmissoes_tempo_cen3.png' salvo.")

def plot_summary_metrics(reno_summaries, bbr_summaries):
    """Gera gráficos de barra com as métricas de resumo agregadas para cenário 3."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Resumo do Desempenho: Cenário 3 (2 Reno vs 1 BBR)', fontsize=16)

    protocols = ['TCP Reno\n(2 hosts)', 'TCP BBR\n(1 host)']
    colors = ['red', 'blue']

    # Calcula as métricas agregadas
    reno_avg_bitrate = sum(s['avg_bitrate'] for s in reno_summaries if s) / len([s for s in reno_summaries if s])
    bbr_avg_bitrate = sum(s['avg_bitrate'] for s in bbr_summaries if s) / len([s for s in bbr_summaries if s])
    
    reno_total_retr = sum(s['total_retr'] for s in reno_summaries if s)
    bbr_total_retr = sum(s['total_retr'] for s in bbr_summaries if s)

    # Gráfico de Vazão Média
    avg_bitrates = [reno_avg_bitrate, bbr_avg_bitrate]
    bars1 = ax1.bar(protocols, avg_bitrates, color=colors, edgecolor='grey', alpha=0.8)
    ax1.set_title('Vazão Média Final', fontsize=14)
    ax1.set_ylabel('Vazão (Mbits/segundo)', fontsize=12)
    for i, v in enumerate(avg_bitrates):
        ax1.text(i, v + 0.1, f"{v:.2f}", ha='center', va='bottom', fontweight='bold')

    # Gráfico de Retransmissões Totais
    total_retrs = [reno_total_retr, bbr_total_retr]
    bars2 = ax2.bar(protocols, total_retrs, color=colors, edgecolor='grey', alpha=0.8)
    ax2.set_title('Total de Retransmissões', fontsize=14)
    ax2.set_ylabel('Número de Retransmissões', fontsize=12)
    for i, v in enumerate(total_retrs):
        ax2.text(i, v + 2, str(v), ha='center', va='bottom', fontweight='bold')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig('grafico_resumo_desempenho_cen3.png', dpi=300, bbox_inches='tight')
    print("Gráfico 'grafico_resumo_desempenho_cen3.png' salvo.")

def plot_latency_comparison(latencies):
    """Gera o gráfico comparativo de latência para cenário 3."""
    labels = ['Reno1\n(Inicial)', 'Reno2\n(Inicial)', 'BBR1\n(Inicial)',
              'Reno1\n(Final)', 'Reno2\n(Final)', 'BBR1\n(Final)']
    
    values = [latencies['reno1_initial'], latencies['reno2_initial'], 
              latencies['bbr1_initial'], latencies['reno1_final'], 
              latencies['reno2_final'], latencies['bbr1_final']]
    
    colors = ['lightcoral', 'lightcoral', 'lightskyblue',
              'red', 'red', 'blue']
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(labels, values, color=colors, edgecolor='grey', alpha=0.8)
    plt.ylabel('Latência Média (ms)', fontsize=12)
    plt.title('Comparativo de Latência Média por Host - Cenário 3 (RTT)', fontsize=16)
    plt.xticks(rotation=0)
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.2, f'{yval:.2f}', 
                ha='center', va='bottom', fontsize=10, fontweight='bold')
        
    plt.tight_layout()
    plt.savefig('grafico_comparativo_latencia_cen3.png', dpi=300, bbox_inches='tight')
    print("Gráfico 'grafico_comparativo_latencia_cen3.png' salvo.")

def plot_individual_host_throughput(reno_data_list, bbr_data_list):
    """Gera gráfico comparativo da vazão individual de cada host para cenário 3."""
    plt.figure(figsize=(14, 8))
    
    # Plotar dados do Reno
    reno_colors = ['red', 'darkred']
    for i, data in enumerate(reno_data_list):
        if data['times']:
            plt.plot(data['times'], data['bitrates'], marker='x', linestyle='--', 
                    label=f'TCP Reno H{i+1}', color=reno_colors[i], linewidth=2)
    
    # Plotar dados do BBR
    for i, data in enumerate(bbr_data_list):
        if data['times']:
            plt.plot(data['times'], data['bitrates'], marker='o', linestyle='-', 
                    label=f'TCP BBR H{i+1}', color='blue', linewidth=2)
    
    plt.title('Vazão Individual de Cada Host - Cenário 3 (2 Reno vs 1 BBR)', fontsize=16)
    plt.xlabel('Tempo (segundos)', fontsize=12)
    plt.ylabel('Vazão (Mbits/segundo)', fontsize=12)
    plt.legend()
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.tight_layout()
    plt.savefig('grafico_vazao_individual_cen3.png', dpi=300, bbox_inches='tight')
    print("Gráfico 'grafico_vazao_individual_cen3.png' salvo.")

def parse_http_metrics(content):
    """Extrai métricas de desempenho HTTP das requisições simultâneas."""
    metrics = {
        'reno1': [], 'reno2': [], 'bbr1': []
    }
    
    # Padrão para extrair métricas HTTP
    pattern = re.compile(r"=== MÉTRICAS (H_\w+)_Simultaneous_\d+ ===\s+Tempo total: ([\d\.]+)s\s+Tempo de conexão: ([\d\.]+)s\s+Tempo de transferência: ([\d\.]+)s\s+Velocidade de download: ([\d\.]+) bytes/s")
    
    for match in pattern.finditer(content):
        host = match.group(1).lower()
        total_time = float(match.group(2))
        connection_time = float(match.group(3))
        transfer_time = float(match.group(4))
        download_speed = float(match.group(5))
        
        if 'reno1' in host:
            metrics['reno1'].append({
                'total_time': total_time,
                'connection_time': connection_time,
                'transfer_time': transfer_time,
                'download_speed': download_speed / 1000  # Convert to KB/s
            })
        elif 'reno2' in host:
            metrics['reno2'].append({
                'total_time': total_time,
                'connection_time': connection_time,
                'transfer_time': transfer_time,
                'download_speed': download_speed / 1000
            })
        elif 'bbr1' in host:
            metrics['bbr1'].append({
                'total_time': total_time,
                'connection_time': connection_time,
                'transfer_time': transfer_time,
                'download_speed': download_speed / 1000
            })
    
    return metrics

def plot_http_performance(http_metrics):
    """Gera gráfico de desempenho HTTP para cenário 3."""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Desempenho HTTP - Cenário 3 (Requisições Simultâneas)', fontsize=16)
    
    hosts = ['Reno1', 'Reno2', 'BBR1']
    colors = ['red', 'darkred', 'blue']
    
    # Calcular médias
    avg_total_time = []
    avg_connection_time = []
    avg_transfer_time = []
    avg_download_speed = []
    
    for host in ['reno1', 'reno2', 'bbr1']:
        if http_metrics[host]:
            avg_total_time.append(np.mean([m['total_time'] for m in http_metrics[host]]))
            avg_connection_time.append(np.mean([m['connection_time'] for m in http_metrics[host]]))
            avg_transfer_time.append(np.mean([m['transfer_time'] for m in http_metrics[host]]))
            avg_download_speed.append(np.mean([m['download_speed'] for m in http_metrics[host]]))
        else:
            avg_total_time.append(0)
            avg_connection_time.append(0)
            avg_transfer_time.append(0)
            avg_download_speed.append(0)
    
    # Gráfico 1: Tempo Total
    bars1 = ax1.bar(hosts, avg_total_time, color=colors, alpha=0.8, edgecolor='grey')
    ax1.set_title('Tempo Total Médio', fontsize=14)
    ax1.set_ylabel('Tempo (segundos)', fontsize=12)
    for i, v in enumerate(avg_total_time):
        ax1.text(i, v + 0.005, f"{v:.3f}", ha='center', va='bottom', fontweight='bold')
    
    # Gráfico 2: Tempo de Conexão
    bars2 = ax2.bar(hosts, avg_connection_time, color=colors, alpha=0.8, edgecolor='grey')
    ax2.set_title('Tempo de Conexão Médio', fontsize=14)
    ax2.set_ylabel('Tempo (segundos)', fontsize=12)
    for i, v in enumerate(avg_connection_time):
        ax2.text(i, v + 0.001, f"{v:.3f}", ha='center', va='bottom', fontweight='bold')
    
    # Gráfico 3: Tempo de Transferência
    bars3 = ax3.bar(hosts, avg_transfer_time, color=colors, alpha=0.8, edgecolor='grey')
    ax3.set_title('Tempo de Transferência Médio', fontsize=14)
    ax3.set_ylabel('Tempo (segundos)', fontsize=12)
    for i, v in enumerate(avg_transfer_time):
        ax3.text(i, v + 0.002, f"{v:.3f}", ha='center', va='bottom', fontweight='bold')
    
    # Gráfico 4: Velocidade de Download
    bars4 = ax4.bar(hosts, avg_download_speed, color=colors, alpha=0.8, edgecolor='grey')
    ax4.set_title('Velocidade de Download Média', fontsize=14)
    ax4.set_ylabel('Velocidade (KB/s)', fontsize=12)
    for i, v in enumerate(avg_download_speed):
        ax4.text(i, v + 5, f"{v:.1f}", ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig('grafico_desempenho_http_cen3.png', dpi=300, bbox_inches='tight')
    print("Gráfico 'grafico_desempenho_http_cen3.png' salvo.")

if __name__ == '__main__':
    try:
        with open('c3_resultados.txt', 'r') as f:
            content = f.read()

        # Parsear dados de cada host individualmente
        reno_data_list = [
            parse_iperf_data(content, 'H_Reno1'),
            parse_iperf_data(content, 'H_Reno2')
        ]
        
        bbr_data_list = [
            parse_iperf_data(content, 'H_BBR1')
        ]

        # Combinar dados por protocolo
        reno_combined = combine_protocol_data(reno_data_list)
        bbr_combined = combine_protocol_data(bbr_data_list)

        # Parsear estatísticas de resumo
        reno_summaries = [
            parse_summary_stats(content, 'H_Reno1'),
            parse_summary_stats(content, 'H_Reno2')
        ]
        
        bbr_summaries = [
            parse_summary_stats(content, 'H_BBR1')
        ]
        
        # Parsear latências
        latencies = {
            'reno1_initial': parse_latency(content, 'H_Reno1', ''),
            'reno2_initial': parse_latency(content, 'H_Reno2', ''),
            'bbr1_initial': parse_latency(content, 'H_BBR1', ''),
            'reno1_final': parse_latency(content, 'H_Reno1', 'Final'),
            'reno2_final': parse_latency(content, 'H_Reno2', 'Final'),
            'bbr1_final': parse_latency(content, 'H_BBR1', 'Final')
        }

        # Parsear métricas HTTP
        http_metrics = parse_http_metrics(content)

        # Gerar os gráficos
        print("Gerando gráficos para o Cenário 3...")
        
        if reno_combined['times'] and bbr_combined['times']:
            plot_throughput_over_time(reno_combined, bbr_combined)
            plot_retransmissions_over_time(reno_combined, bbr_combined)
            plot_individual_host_throughput(reno_data_list, bbr_data_list)
        else:
            print("Não foi possível gerar gráficos ao longo do tempo por falta de dados.")

        if all(reno_summaries) and all(bbr_summaries):
            plot_summary_metrics(reno_summaries, bbr_summaries)
        else:
            print("Não foi possível gerar gráfico de resumo por falta de dados.")
            
        if all(latencies.values()):
            plot_latency_comparison(latencies)
        else:
            print("Não foi possível gerar gráfico de latência por falta de dados.")

        if any(http_metrics.values()):
            plot_http_performance(http_metrics)
        else:
            print("Não foi possível gerar gráfico de desempenho HTTP por falta de dados.")

        print("\nTodos os gráficos foram gerados com sucesso para o Cenário 3!")
        print("Arquivos salvos:")
        print("- grafico_vazao_tempo_cen3.png")
        print("- grafico_retransmissoes_tempo_cen3.png")
        print("- grafico_vazao_individual_cen3.png")
        print("- grafico_resumo_desempenho_cen3.png")
        print("- grafico_comparativo_latencia_cen3.png")
        print("- grafico_desempenho_http_cen3.png")

    except FileNotFoundError:
        print("Erro: O arquivo 'c3_resultados.txt' não foi encontrado.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
        import traceback
        traceback.print_exc()