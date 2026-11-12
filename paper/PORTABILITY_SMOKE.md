# KAIRIS — reprodução curta por plataforma

Em um checkout limpo, use Python 3.12 e instale o pacote em um ambiente
virtual. Em Linux ou macOS, execute a partir da raiz do projeto:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/kairis --help
.venv/bin/kairis-setup --check
.venv/bin/python scripts/run_portability_smoke.py --output output/portability-smoke
```

No Windows, use `.venv\Scripts\python.exe` e os executáveis correspondentes.
A instalação acima baixa as dependências Python. O teste executa os cinco
agentes nos seis Randles retrospectivos com as funções opcionais de LLM
desabilitadas. O diretório de saída deve ser novo. O JSON
`output/portability-smoke/portability_evidence.json` registra sistema,
arquitetura, RAM física, Python, bibliotecas, commit, hashes e resultados dos
critérios de aceite dos seis casos. Para comparar ambientes, confira esses
campos e as métricas dentro das tolerâncias registradas.

O workflow **Portability smoke** executa a mesma verificação em Ubuntu, macOS e
Windows. Baixe o artefato de cada job para guardar a evidência. Para evidência
em máquinas de 4–8 GB, execute o mesmo comando num equipamento ou VM com essa
memória. A RAM registrada no JSON identifica o ambiente que efetivamente rodou.
