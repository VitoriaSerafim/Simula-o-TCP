#!/bin/bash

# Script para verificar e instalar dependências necessárias
echo "=== CONFIGURAÇÃO DE DEPENDÊNCIAS PARA SIMULAÇÃO TCP ==="

# Verificar se está sendo executado como root
if [[ $EUID -ne 0 ]]; then
   echo "Este script deve ser executado como root (sudo)"
   exit 1
fi

# Atualizar repositórios
echo "Atualizando repositórios..."
apt-get update -qq

# Instalar dependências básicas
echo "Instalando dependências básicas..."
apt-get install -y python3 python3-pip curl iperf3 tcpdump

# Verificar se o Mininet está instalado
if ! command -v mn &> /dev/null; then
    echo "Mininet não encontrado. Instalando..."
    apt-get install -y mininet
fi

# Verificar módulos TCP disponíveis
echo "Verificando módulos TCP disponíveis..."
echo "Módulos TCP disponíveis:"
cat /proc/sys/net/ipv4/tcp_available_congestion_control

# Verificar se BBR está disponível
if grep -q "bbr" /proc/sys/net/ipv4/tcp_available_congestion_control; then
    echo "✓ TCP BBR está disponível"
else
    echo "⚠ TCP BBR não está disponível. Tentando carregar módulo..."
    modprobe tcp_bbr
    echo "tcp_bbr" >> /etc/modules-load.d/modules.conf
fi

# Verificar se Reno está disponível
if grep -q "reno" /proc/sys/net/ipv4/tcp_available_congestion_control; then
    echo "✓ TCP Reno está disponível"
else
    echo "⚠ TCP Reno não está disponível. Tentando carregar módulo..."
    modprobe tcp_reno
fi

# Configurar permissões
echo "Configurando permissões..."
chmod +x tcp_simulation.py

echo "=== CONFIGURAÇÃO CONCLUÍDA ==="
echo "Você pode executar a simulação com:"
echo "sudo python3 tcp_simulation.py"
