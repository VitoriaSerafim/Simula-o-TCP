#!/bin/bash

# A função 'finish' é executada quando o script termina (ou é interrompido)
# para garantir que quaisquer processos do Mininet sejam limpos.
function finish {
    # Comando para limpar processos do Mininet [4]
    sudo mn -c
    echo "Processos do Mininet limpos."
}
# 'trap finish EXIT' garante que a função 'finish' seja chamada ao sair do script
trap finish EXIT

# Definição de parâmetros gerais do experimento, conforme as instruções do trabalho.
# Estes são os argumentos que o script bufferbloat.py espera [5, 6]
BW_NET=1.5  # Largura de banda do link gargalo (Mb/s), e.g., conexão de uplink lenta [3]
DELAY=10    # Atraso de propagação do link (ms). RTT mínimo entre h1 e h2 é de 20ms, então delay de ida é 10ms [3]
TIME=10     # Duração do experimento em segundos (padrão é 10 segundos) [5]

# --- Parte 2: Experimentos TCP Reno --- [3]

echo "Iniciando experimentos com TCP Reno..."

# Experimento com tamanho de buffer q=100 pacotes
MAXQ=100 # Tamanho do buffer do roteador em pacotes [3]
CONG="reno" # Algoritmo de controle de congestionamento padrão para Reno [6]
DIR_RENO_Q100="results/reno_q100" # Diretório para armazenar os resultados [5]

echo "Executando experimento TCP Reno com maxq=${MAXQ}..."
# O script bufferbloat.py cria o diretório de saída se ele não existir [7]
# Ele deve iniciar um fluxo TCP de longa duração (iperf), um trem de pings e downloads do servidor web simultaneamente [4, 8].
# A congestion control policy é definida via sysctl -w net.ipv4.tcp_congestion_control [7].
sudo python3 bufferbloat.py \
    --bw-net $BW_NET \
    --delay $DELAY \
    --dir $DIR_RENO_Q100 \
    --time $TIME \
    --maxq $MAXQ \
    --cong $CONG # Passa o algoritmo de congestionamento explicitamente [6]

echo "Gerando gráficos para TCP Reno com maxq=${MAXQ}..."
# Os scripts plot_queue.py e plot_ping.py são invocados para gerar os gráficos
# com os nomes específicos esperados.
# 'q.txt' e 'ping.txt' são os arquivos de saída gerados pelo bufferbloat.py no diretório especificado [9].
python3 plot_queue.py "${DIR_RENO_Q100}/q.txt" "reno-buffer-q100.png" # Nome do gráfico da fila [10]
python3 plot_ping.py "${DIR_RENO_Q100}/ping.txt" "reno-rtt-q100.png"   # Nome do gráfico RTT [10]

# Experimento com tamanho de buffer q=20 pacotes
MAXQ=20 # Novo tamanho de buffer para o roteador [4]
DIR_RENO_Q20="results/reno_q20" # Diretório diferente para os novos resultados

echo "Executando experimento TCP Reno com maxq=${MAXQ}..."
sudo python3 bufferbloat.py \
    --bw-net $BW_NET \
    --delay $DELAY \
    --dir $DIR_RENO_Q20 \
    --time $TIME \
    --maxq $MAXQ \
    --cong $CONG

echo "Gerando gráficos para TCP Reno com maxq=${MAXQ}..."
python3 plot_queue.py "${DIR_RENO_Q20}/q.txt" "reno-buffer-q20.png" # Nome do gráfico da fila [10]
python3 plot_ping.py "${DIR_RENO_Q20}/ping.txt" "reno-rtt-q20.png"   # Nome do gráfico RTT [10]

echo "Experimentos TCP Reno concluídos."