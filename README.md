# KAIRIS

**Kramers–Kronig-Assessed Impedance, Relaxation, and Integrated Spectroscopy**

> Este é o ramo `standalone/esc`. Para usar somente o método original ESC,
> consulte [STANDALONE_ESC.md](STANDALONE_ESC.md). O protocolo integrado permanece
> na branch `main`.

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

### Linux e macOS

```bash
chmod +x scripts/setup_kairis.sh scripts/start_kairis.sh
./scripts/setup_kairis.sh
./scripts/start_kairis.sh --no-open
```

No Linux, o instalador reconhece `apt`, `dnf`, `pacman` e `zypper`. No macOS, usa
o Python já instalado ou oferece `python@3.12` pelo Homebrew. Se o Homebrew não
existir, exibe as instruções oficiais sem instalá-lo silenciosamente. Em qualquer
sistema, a instalação é oferecida antes de qualquer alteração.

O projeto também é um pacote Python instalável. Dentro do clone:

```bash
python -m pip install -e .
kairis --help
kairis-web --no-open
```

Os comandos instalados usam a pasta atual como área de trabalho quando executados
fora de um clone. Defina `KAIRIS_WORKSPACE` para escolher outra pasta.

## Atualização automática segura

Durante a configuração inicial, o assistente pergunta uma vez se o pesquisador
autoriza atualizações automáticas de código e dependências. A escolha fica somente
em `config/local_config.json`, que não é versionado. Quando autorizada, os scripts
de inicialização executam o atualizador antes de abrir o painel ou iniciar o modo
contínuo.

O atualizador:

- usa apenas fast-forward da branch configurada;
- nunca sobrescreve alterações locais versionadas;
- continua com a versão instalada quando não há rede;
- sincroniza `requirements.lock` somente quando ele mudou;
- registra o resultado em `output/update_status.json`;
- registra o commit Git usado na proveniência de cada amostra.

A instalação precisa ser um clone Git com o remoto `origin`. Para obter o clone
oficial já configurado:

```bash
git clone https://github.com/Emanuel-963/KAIRIS.git
cd KAIRIS
```

Downloads por arquivo ZIP não contêm os metadados Git necessários para atualização.
Para iniciar excepcionalmente sem consultar atualizações:

```powershell
.\scripts\start_kairis.ps1 -NoUpdate
```

```bash
./scripts/start_kairis.sh --no-update --no-open
```

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

O interruptor **LLM local pelo Ollama** controla a interpretação tanto na execução
única quanto no modo contínuo. Durante o monitoramento, uma mudança passa a valer
antes da próxima amostra, sem reiniciar o processo. Quando desligada, a análise por
regras continua funcionando normalmente.
O campo **Atualização** mostra se a instalação está em dia, sem rede, sem remoto ou
bloqueada por alterações locais.

Execução manual no Windows:

```powershell
.\.venv\Scripts\python.exe web_app.py
```

Execução manual no Linux ou macOS:

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

Também é possível escolher explicitamente o uso da LLM pela linha de comando:

```bash
python run_pipeline.py --input data/input --output output --llm
python run_pipeline.py --input data/input --output output --no-llm
```

Arquivos homônimos em subpastas recebem identificadores com o caminho relativo, como
`celula_1__espectro`, impedindo sobrescrita de métricas e relatórios.

Todos os JSONs, SVGs e HTMLs são gravados de forma atômica. O JSON consolidado e o
rodapé do relatório incluem SHA-256 da entrada, timestamp, versões científicas e a
configuração efetiva sem segredos.

## Memória persistente do orquestrador

O Ollama não mantém memória entre requisições por conta própria. O KAIRIS salva um
histórico estruturado de cada amostra em `output/memory/kairis_memory.json`, contendo
métricas, regras e a conclusão da LLM. O histórico completo permanece no arquivo,
inclusive quando a LLM está desligada.

Para preservar o desempenho de modelos pequenos, apenas uma janela recente é
incluída em cada prompt. Ela é configurada por:

- `llm_memory_enabled`: ativa ou desativa o uso e a gravação da memória;
- `llm_memory_recent_records`: número máximo de execuções anteriores no prompt;
- `llm_memory_max_prompt_chars`: limite de caracteres da memória enviada à LLM.

A memória serve como contexto comparativo. As métricas da amostra atual continuam
sendo a fonte primária e não são substituídas por conclusões anteriores.

## Aprendizado supervisionado por pesquisadores

Cada relatório no painel pode ser marcado como **Aprovar**, **Corrigir** ou
**Rejeitar**. O KAIRIS mantém o histórico completo das avaliações e reconstrói
automaticamente um dataset supervisionado após cada decisão:

- `output/training/feedback.json`: trilha de auditoria de todas as revisões;
- `output/training/dataset.jsonl`: somente a revisão mais recente de cada espectro,
  incluindo aprovadas e corrigidas; rejeitadas ficam fora do dataset.

Exemplos validados passam a ser usados imediatamente como few-shot no prompt do
Ollama. Isso melhora o comportamento sem treinamento pesado e é adequado aos PCs de
4–8 GB. O painel permite baixar o JSONL e mostra o progresso até o mínimo configurado
por `finetune_min_validated_examples`.

O ajuste real dos pesos não é executado silenciosamente. Ele exige um modelo-base
definido, ambiente separado com GPU e validação do dataset. Consulte
[`TRAINING.md`](TRAINING.md) para o fluxo e as garantias adotadas.

## Corpus amplo de validação EIS

O projeto inclui o **KAIRIS EIS Validation Corpus v1** em
`data/validation/kairis_eis_validation_v1`: 72 espectros sintéticos KAIRIS, 72
espectros rotulados do AutoECM (45 treino + 27 holdout) e 54 espectros
experimentais públicos, totalizando 198 entradas diretamente executáveis. As duas
fontes publicadas são CC BY 4.0.
O manifesto registra origem, licença, papel recomendado e SHA-256. Para auditar a
leitura de todos os arquivos ou executar Agentes 1–5 sem LLM:

```bash
python scripts/validate_eis_corpus.py
python scripts/validate_eis_corpus.py --full-pipeline
```

Consulte o README dentro do corpus antes de usar os dados para treinamento. Dados
experimentais públicos são tratados como avaliação externa sem rótulo causal;
interpretações da LLM só entram no dataset supervisionado após revisão humana.

### Validação de uma release limpa

O plano científico e os critérios de desenvolvimento estão em
`paper/VALIDATION_PLAN_v1.md` e `config/validation_acceptance_v1.json`. Para uma
execução candidata à publicação, use um commit limpo, uma tag exata e um diretório
de saída novo:

```powershell
python scripts/run_release_validation.py `
  --output output/validation_release_v1 `
  --require-tag
```

O comando não reutiliza resultados, mantém as evidências fora do corpus
versionado e falha se a proveniência ou os critérios de referência Randles não
forem satisfeitos. Os 198 espectros atuais já foram examinados durante o
desenvolvimento e, portanto, são validação retrospectiva, não um holdout
confirmatório intocado.

Para caracterizar retrospectivamente a recuperação de R∞ e dos tempos de
relaxação sintéticos identificáveis, e para preparar a revisão humana cega:

```bash
python scripts/analyze_synthetic_recovery.py --output output/validation_release_v1
python scripts/build_blinded_review_pack.py \
  --output output/validation_release_v1 \
  --destination output/blinded_review_pack_v1
```

O segundo comando cria dados e figuras anonimizados em `reviewer/` e mantém a
chave em `coordinator_only/`, que não deve ser entregue aos especialistas. O
procedimento completo está em `paper/BLINDED_REVIEW_PROTOCOL_v1.md`.

O benchmark controlado de robustez gera dados tabulares e uma figura SVG com
resolução de processos, sensibilidade a ruído e efeito da frequência máxima:

```bash
python scripts/run_robustness_benchmark.py \
  --destination output/robustness_benchmark_v1 \
  --replicates 20
```

Cinco réplicas são suficientes para uma execução piloto; para resultados do
artigo, use pelo menos 20 e registre a semente, o commit e o ambiente gravados no
JSON do benchmark.

### Confiabilidade e abstenção de R∞

O KAIRIS preserva `R_inf` como valor bruto auditável, mas só preenche
`R_inf_accepted` quando a borda de alta frequência satisfaz os critérios
configurados de fase e platô de Re(Z). Em caso de abstenção, a síntese e o HTML
mostram um alerta, e o ESC G4 também se abstém se depender do fallback de R∞.
Uma referência G4 obtida independentemente por geometria e condutividade continua
válida. Os limiares ficam em `config/protocol_config.json`.

Quando habilitada, a extrapolação secundária ajusta
`R∞ + A(jω)^(-n)` em janelas aninhadas. Ela é exibida separadamente, nunca
substitui `R_inf_accepted`, não alimenta G4 e fornece apenas uma faixa de
sensibilidade à janela. A contagem DRT também é marcada como indeterminada para
um pico isolado ou não resolvida quando picos detectados estão separados por
menos de 1,3 década.

Depois que dois especialistas preencherem formulários independentes, calcule a
concordância sem abrir a chave cega:

```bash
python scripts/analyze_blinded_reviews.py reviewer_a.csv reviewer_b.csv \
  --destination output/review_agreement_v1
```

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

## Contribuição e suporte

Contribuições científicas, novos formatos de arquivo, testes e melhorias de
documentação são bem-vindos. Consulte [CONTRIBUTING.md](CONTRIBUTING.md) antes de
abrir uma alteração. Problemas reproduzíveis e solicitações de suporte podem ser
registrados no GitHub Issues sem anexar dados experimentais confidenciais.

## Licenças

O código-fonte e a documentação do KAIRIS são distribuídos sob a licença BSD
3-Clause, disponível em [LICENSE](LICENSE). Dados de terceiros mantêm suas
licenças originais e não são relicenciados pela licença do software. A
proveniência e as condições dos conjuntos públicos incluídos estão descritas em
[data/validation/kairis_eis_validation_v1/ATTRIBUTION.md](data/validation/kairis_eis_validation_v1/ATTRIBUTION.md).
