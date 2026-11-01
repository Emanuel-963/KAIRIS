# KAIRIS

Pipeline científico sem circuito equivalente para espectroscopia de impedância
eletroquímica. O KAIRIS executa EIS → DRT → GSF → ESC e produz um relatório HTML
interativo pelo navegador.

## Instalação assistida

Os instaladores verificam Python, criam o ambiente virtual, instalam as dependências
e detectam a memória RAM. Nenhum download do Ollama ou de modelos ocorre sem uma
confirmação explícita.

### Windows

Abra o PowerShell na pasta do projeto:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup_kairis.ps1
.\scripts\start_kairis.ps1
```

Se Python não estiver instalado, o assistente oferece Python 3.12 pelo `winget`.

### Linux

```bash
chmod +x scripts/setup_kairis.sh scripts/start_kairis.sh
./scripts/setup_kairis.sh
./scripts/start_kairis.sh --no-open
```

O instalador reconhece `apt`, `dnf`, `pacman` e `zypper`. Se Python estiver ausente,
a instalação é oferecida antes de qualquer alteração no sistema.

## Ollama opcional e escolha por memória

O protocolo funciona integralmente sem LLM, usando a interpretação determinística.
O assistente consulta a RAM e recomenda:

| Memória física | Perfil | Modelo recomendado |
|---|---|---|
| menos de 6 GB | computador de 4 GB | `gemma3:1b` |
| 6 a 11,9 GB | computador de 8 GB | `qwen3:4b-instruct-2507-q4_K_M` |
| 12 GB ou mais | computador de 16 GB+ | `qwen3:4b-instruct-2507-q4_K_M` |

Instalar o Ollama e baixar o modelo são decisões separadas e opcionais. Para verificar
o computador sem instalar nada:

```bash
python setup_kairis.py --check
```

Para configurar sem oferecer Ollama:

```bash
python setup_kairis.py --skip-ollama
```

## Painel web

O painel local fica disponível em `http://127.0.0.1:8000`. Ele permite enviar
arquivos EIS `.txt` ou `.csv`, executar o pipeline, ativar o monitoramento contínuo,
acompanhar agentes e abrir relatórios. O carregador reconhece automaticamente
separadores tabulação ou ponto e vírgula e cabeçalhos com `-Im(Z)`, `-Z''`, `Im(Z)`
ou `Z''`, preservando corretamente a convenção de sinal indicada pelo cabeçalho.

Execução manual no Windows:

```powershell
.\.venv\Scripts\python.exe web_app.py
```

Execução manual no Linux:

```bash
.venv/bin/python web_app.py --no-open
```

## Linha de comando

Execução única:

```bash
python run_pipeline.py --input data/input --output output
```

Por padrão, uma amostra que já possui `output/metrics/<amostra>_metrics.json` é
ignorada. Para reprocessar e substituir seus artefatos explicitamente:

```bash
python run_pipeline.py --input data/input --output output --overwrite
```

Monitoramento contínuo:

```bash
python run_pipeline.py --input data/input --output output --watch
```

Arquivos homônimos em subpastas recebem identificadores com o caminho relativo, como
`celula_1__espectro`, impedindo sobrescrita de métricas e relatórios.

Todos os JSONs, SVGs e HTMLs são gravados de forma atômica. O JSON consolidado e o
rodapé do relatório incluem SHA-256 da entrada, timestamp, versões científicas e a
configuração efetiva sem segredos.

## Relatórios offline

O padrão carrega D3.js pelo CDN. Para gerar um HTML que também incorpore o D3, defina
`"report_d3_inline": true` em `config/protocol_config.json`. Na primeira geração o
bundle é baixado para `web/static/d3.min.js`; as seguintes reutilizam esse cache.

## Docker

Por padrão, o contêiner usa somente as regras determinísticas e não contém Ollama:

```bash
docker compose up --build
```

Abra `http://127.0.0.1:8000`. Entrada e saída são montadas em `data/input` e
`output` no computador hospedeiro.

Para usar um Ollama instalado no hospedeiro, altere em `compose.yaml`:

```yaml
environment:
  KAIRIS_LLM_ENABLED: "true"
  KAIRIS_OLLAMA_URL: "http://host.docker.internal:11434"
  KAIRIS_OLLAMA_MODEL: "gemma3:1b"
```

O serviço Ollama precisa aceitar a conexão vinda do Docker. Não exponha a porta do
Ollama em redes públicas.

## Resultados

- `output/reports`: relatórios HTML.
- `output/metrics`: métricas JSON.
- `output/figures`: figuras SVG estáticas do GSF.
- `output/pipeline.log`: log de processamento.

## Testes

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python setup_kairis.py --check
```

Para uma instalação reproduzível de produção, use o arquivo travado:

```bash
python -m pip install -r requirements.lock
```

Atualize-o, quando necessário, com:

```bash
python -m piptools compile requirements.txt --output-file requirements.lock
```
