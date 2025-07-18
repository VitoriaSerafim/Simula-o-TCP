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

def parse_iperf_data(content, protocol_id):
    """
    Extrai dados de vazão e retransmissão, agora mais robusto para diferentes unidades.
    """
    section_pattern = re.compile(f"=== IPERF3 {protocol_id}_Throughput ===(.*?)iperf Done.", re.DOTALL)
    section_match = section_pattern.search(content)

    if not section_match:
        print(f"Aviso: Seção iperf para {protocol_id} não encontrada.")
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

def parse_summary_stats(content, protocol_id):
    """
    Extrai a vazão média final e o total de retransmissões com regex mais flexível.
    """
    section_pattern = re.compile(f"=== IPERF3 {protocol_id}_Throughput ===(.*?)iperf Done.", re.DOTALL)
    section_match = section_pattern.search(content)
    if not section_match:
        return None

    summary_pattern = re.compile(r"\[\s+\d+\]\s+0\.00-[\d\.]+\s+sec.*?([\d\.]+)\s+Mbits/sec\s+(\d+)\s+sender")
    match = summary_pattern.search(section_match.group(1))

    if match:
        avg_bitrate = float(match.group(1))
        total_retr = int(match.group(2))
        return {'avg_bitrate': avg_bitrate, 'total_retr': total_retr}
    
    print(f"Aviso: Estatísticas de resumo para {protocol_id} não encontradas.")
    return {'avg_bitrate': 0, 'total_retr': 0}

def parse_latency(content, protocol_id, stage):
    """
    Extrai a latência média (RTT) com regex que ignora textos extras como (Reno).
    """
    # Regex flexível para o título da seção
    pattern_str = f"=== LATÊNCIA {protocol_id}.*{stage}.*===\s+rtt min/avg/max/mdev = .*?/([\d\.]+)/.*/.*ms"
    pattern = re.compile(pattern_str)
    match = pattern.search(content)

    if match:
        return float(match.group(1))
    
    print(f"Aviso: Latência para {protocol_id} ({stage}) não encontrada.")
    return 0

def plot_throughput_over_time(reno_data, bbr_data):
    """Gera o gráfico de vazão ao longo do tempo."""
    plt.figure(figsize=(12, 7))
    plt.plot(reno_data['times'], reno_data['bitrates'], marker='x', linestyle='--', label='TCP Reno (H1)', color='red')
    plt.plot(bbr_data['times'], bbr_data['bitrates'], marker='o', linestyle='-', markersize=5, label='TCP BBR (H2)', color='blue')
    plt.title('Vazão de TCP Reno vs. BBR ao Longo do Tempo', fontsize=16)
    plt.xlabel('Tempo (segundos)', fontsize=12)
    plt.ylabel('Vazão (Mbits/segundo)', fontsize=12)
    plt.legend()
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.tight_layout()
    plt.savefig('grafico_vazao_tempo.png')
    print("Gráfico 'grafico_vazao_tempo.png' salvo.")

def plot_retransmissions_over_time(reno_data, bbr_data):
    """
    Gera o gráfico de retransmissões, com proteção contra listas de tamanhos diferentes.
    """
    plt.figure(figsize=(12, 7))
    
    # Garante que ambas as listas tenham o mesmo tamanho para plotagem
    max_len = max(len(reno_data['times']), len(bbr_data['times']))
    
    # === INÍCIO DA CORREÇÃO ===
    # Corrigido: usa len(reno_data['retrs']) em vez de len(reno_retrs)
    reno_retrs = reno_data['retrs'] + [0] * (max_len - len(reno_data['retrs']))
    bbr_retrs = bbr_data['retrs'] + [0] * (max_len - len(bbr_data['retrs']))
    # === FIM DA CORREÇÃO ===

    # O preenchimento das listas de tempo também precisa da mesma correção
    reno_times = reno_data['times'] + [0] * (max_len - len(reno_data['times']))
    bbr_times = bbr_data['times'] + [0] * (max_len - len(bbr_data['times']))

    bar_width = 0.4
    r1 = np.arange(max_len)
    r2 = [x + bar_width for x in r1]
    
    xtick_labels = reno_times if len(reno_times) >= len(bbr_times) else bbr_times

    plt.bar(r1, reno_retrs, color='red', width=bar_width, edgecolor='grey', label='TCP Reno (H1)')
    plt.bar(r2, bbr_retrs, color='blue', width=bar_width, edgecolor='grey', label='TCP BBR (H2)')

    plt.title('Retransmissões por Segundo (Reno vs. BBR)', fontsize=16)
    plt.xlabel('Tempo (segundos)', fontsize=12)
    plt.ylabel('Número de Retransmissões', fontsize=12)
    plt.xticks([r + bar_width/2 for r in range(max_len)], [int(t) for t in xtick_labels], rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.savefig('grafico_retransmissoes_tempo.png')
    print("Gráfico 'grafico_retransmissoes_tempo.png' salvo.")

def plot_summary_metrics(reno_summary, bbr_summary):
    """Gera gráficos de barra com as métricas de resumo."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Resumo do Desempenho: Vazão Média e Retransmissões Totais', fontsize=16)

    protocols = ['TCP Reno (H1)', 'TCP BBR (H2)']
    colors = ['red', 'blue']

    # Gráfico de Vazão Média
    avg_bitrates = [reno_summary['avg_bitrate'], bbr_summary['avg_bitrate']]
    ax1.bar(protocols, avg_bitrates, color=colors, edgecolor='grey')
    ax1.set_title('Vazão Média Final', fontsize=14)
    ax1.set_ylabel('Vazão (Mbits/segundo)', fontsize=12)
    for i, v in enumerate(avg_bitrates):
        ax1.text(i, v + 0.1, f"{v:.2f}", ha='center', va='bottom')

    # Gráfico de Retransmissões Totais
    total_retrs = [reno_summary['total_retr'], bbr_summary['total_retr']]
    ax2.bar(protocols, total_retrs, color=colors, edgecolor='grey')
    ax2.set_title('Total de Retransmissões', fontsize=14)
    ax2.set_ylabel('Número de Retransmissões', fontsize=12)
    for i, v in enumerate(total_retrs):
        ax2.text(i, v + 1, str(v), ha='center', va='bottom')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig('grafico_resumo_desempenho.png')
    print("Gráfico 'grafico_resumo_desempenho.png' salvo.")

def plot_latency_comparison(latencies):
    """Gera o gráfico comparativo de latência."""
    labels = ['Reno (Inicial)', 'BBR (Inicial)', 'Reno (Final)', 'BBR (Final)']
    values = [latencies['reno_initial'], latencies['bbr_initial'], latencies['reno_final'], latencies['bbr_final']]
    colors = ['lightcoral', 'lightskyblue', 'red', 'blue']
    
    plt.figure(figsize=(10, 6))
    bars = plt.bar(labels, values, color=colors, edgecolor='grey')
    plt.ylabel('Latência Média (ms)', fontsize=12)
    plt.title('Comparativo de Latência Média (RTT)', fontsize=16)
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.1, f'{yval:.2f}', ha='center', va='bottom')
        
    plt.tight_layout()
    plt.savefig('grafico_comparativo_latencia.png')
    print("Gráfico 'grafico_comparativo_latencia.png' salvo.")


if __name__ == '__main__':
    try:
        with open('c2_resultados.txt', 'r') as f:
            content = f.read()

        # Parsear todos os dados com as funções corrigidas
        reno_iperf_data = parse_iperf_data(content, 'H1')
        bbr_iperf_data = parse_iperf_data(content, 'H2')

        reno_summary = parse_summary_stats(content, 'H1')
        bbr_summary = parse_summary_stats(content, 'H2')
        
        latencies = {
            'reno_initial': parse_latency(content, 'H1', ''),
            'bbr_initial': parse_latency(content, 'H2', ''),
            'reno_final': parse_latency(content, 'H1', 'Final'),
            'bbr_final': parse_latency(content, 'H2', 'Final')
        }

        # Gerar os gráficos
        if reno_iperf_data['times'] and bbr_iperf_data['times']:
            plot_throughput_over_time(reno_iperf_data, bbr_iperf_data)
            plot_retransmissions_over_time(reno_iperf_data, bbr_iperf_data)
        else:
            print("Não foi possível gerar gráficos ao longo do tempo por falta de dados.")

        if reno_summary and bbr_summary:
            plot_summary_metrics(reno_summary, bbr_summary)
        else:
            print("Não foi possível gerar gráfico de resumo por falta de dados.")
            
        if all(latencies.values()):
            plot_latency_comparison(latencies)
        else:
            print("Não foi possível gerar gráfico de latência por falta de dados.")

    except FileNotFoundError:
        print("Erro: O arquivo 'c1_resultados.txt' não foi encontrado.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")