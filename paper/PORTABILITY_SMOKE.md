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
Windows. O envio de um ramo `release/*` ao GitHub também executa os 198
espectros retrospectivos em cada plataforma. Nas execuções manuais, use
a opção `full_corpus`. Os artefatos `portability-full-*`
incluem o manifesto do ambiente, a avaliação dos dez critérios e o log.

Para executar o mesmo teste integral em uma máquina independente, rode
na raiz do checkout com o ambiente Python ativo:

```sh
python scripts/run_release_validation.py --output output/portability-full
```

Repita em uma máquina ou VM com 4 GB e outra com 8 GB para documentar esses
perfis. Registre a RAM efetiva, o commit, os hashes do manifesto e da
configuração, o tempo de execução e o resultado dos critérios a partir do
diretório `output/portability-full/evidence/`.
