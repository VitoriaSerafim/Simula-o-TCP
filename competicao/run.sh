# 1. Salvar o script principal
sudo nano tcp_simulation.py
# (cole o código do primeiro artifact)

# 2. Salvar o script de dependências  
sudo nano setup_dependencies.sh
# (cole o código do segundo artifact)

# 3. Executar configuração
sudo chmod +x setup_dependencies.sh
sudo ./setup_dependencies.sh

# 4. Executar simulação
sudo python3 tcp_simulation.py
