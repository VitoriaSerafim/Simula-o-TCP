#!/bin/bash

# Nota: O Mininet deve ser executado como root. Invoque este script com sudo.

time=90
bwnet=1.5
# Se o RTT total é 20ms, o delay em cada um dos dois links deve ser 10ms.
delay=10

iperf_port=5001

for qsize in 20 100; do
    dir=bbr-q$qsize

    # Executa o script bufferbloat.py com os parâmetros para BBR
    sudo python3 bufferbloat.py \
        --bw-net $bwnet \
        --delay $delay \
        -t $time \
        --maxq $qsize \
        --dir $dir \
        --cong bbr  # Usa o algoritmo de controle de congestionamento BBR

    # Gera os gráficos a partir dos arquivos de saída com os novos nomes
    python3 plot_queue.py -f $dir/q.txt -o bbr-buffer-q$qsize.png
    python3 plot_ping.py -f $dir/ping.txt -o bbr-rtt-q$qsize.png
done