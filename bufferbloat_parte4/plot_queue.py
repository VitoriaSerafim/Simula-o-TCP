import matplotlib.pyplot as plt
import sys

# Verifica se os argumentos foram passados corretamente
if len(sys.argv) != 3:
    print("Uso: python3 plot_queue.py <arquivo_q.txt> <nome_imagem.png>")
    sys.exit(1)

arquivo_dados = sys.argv[1]
arquivo_saida = sys.argv[2]

tempos = []
tamanhos_fila = []

# Lê o arquivo de dados
with open(arquivo_dados, 'r') as f:
    for linha in f:
        partes = linha.strip().split()
        if len(partes) >= 2:
            tempos.append(float(partes[0]))
            tamanhos_fila.append(int(partes[1]))

# Plota o gráfico
plt.figure(figsize=(10, 4))
plt.plot(tempos, tamanhos_fila, label='Tamanho da Fila (pacotes)', color='blue')
plt.xlabel("Tempo (s)")
plt.ylabel("Tamanho da Fila (pacotes)")
plt.title("Tamanho da Fila ao Longo do Tempo")
plt.grid(True)
plt.tight_layout()
plt.savefig(arquivo_saida)
print(f"Gráfico salvo como {arquivo_saida}")