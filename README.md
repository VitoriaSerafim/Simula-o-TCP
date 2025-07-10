# Experimento: Bufferbloat com Mininet (TCP Reno vs TCP BBR)

## 📋 Descrição

Este repositório contém a implementação do experimento da disciplina **Redes de Computadores (IC/UFRJ)** para análise do fenômeno **Bufferbloat** usando o emulador de redes **Mininet**. O objetivo é comparar o desempenho dos algoritmos de controle de congestionamento **TCP Reno** e **TCP BBR** em diferentes tamanhos de buffer do roteador.

---

## 🏗️ Estrutura do Projeto

Os principais arquivos incluídos neste repositório são:

| Arquivo | Descrição |
|--------|-----------|
| `run.sh` | Executa o experimento com TCP Reno |
| `run_bbr.sh` | Executa o experimento com TCP BBR |
| `bufferbloat.py` | Define a topologia de rede e coleta dados (RTT, cwnd, fila) |
| `monitor.py` | Monitora a fila do roteador |
| `plot_queue.py` | Gera gráfico da ocupação da fila |
| `plot_ping.py` | Gera gráfico de RTT via ping |
| `plot_defaults.py` | Funções auxiliares para gráficos |
| `helper.py` | Funções utilitárias diversas |
| `webserver.py` | Inicia o servidor web para simular navegação |
| `index.html` | Página web a ser baixada pelos testes |

---

## 🖥️ Ambiente de Execução

O experimento deve ser executado dentro de uma máquina virtual Mininet baseada em **Ubuntu 20.04**, conforme descrito nas instruções oficiais:

📦 [Mininet Vagrant VM](https://github.com/kaichengyan/mininet-vagrant)

### Pré-requisitos:

Dentro da VM, execute:

```bash
sudo apt-get update
sudo apt install python3-pip
sudo python3 -m pip install mininet matplotlib

