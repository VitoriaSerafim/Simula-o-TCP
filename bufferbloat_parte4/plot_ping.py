import matplotlib.pyplot as plt
import sys

def parse_ping(fname):
    ret = []
    lines = open(fname).readlines()
    num = 0
    for line in lines:
        if 'bytes from' not in line:
            continue
        try:
            rtt = line.split(' ')[-2]
            rtt = rtt.split('=')[1]
            rtt = float(rtt)
            ret.append([num, rtt])
            num += 1
        except:
            continue
    return ret

def main():
    if len(sys.argv) != 3:
        print("Uso: python3 plot_ping.py <arquivo ping.txt> <arquivo_saida.png>")
        sys.exit(1)

    entrada = sys.argv[1]
    saida = sys.argv[2]

    data = parse_ping(entrada)
    x = [p[0] for p in data]
    y = [p[1] for p in data]

    x = [i / 10 for i in x]  # assumindo 10 pings por segundo
    plt.figure(figsize=(12, 5))
    plt.plot(x, y, label='RTT (ms)')
    plt.xlabel("Tempo (s)")
    plt.ylabel("RTT (ms)")
    plt.title("Variação do RTT ao longo do tempo")
    plt.grid(True)
    plt.savefig(saida)
    print(f"Gráfico salvo em {saida}")

if __name__ == "__main__":
    main()