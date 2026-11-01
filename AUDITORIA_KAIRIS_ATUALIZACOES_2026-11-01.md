# Nova auditoria do KAIRIS — atualizações, mudanças e estado verificável

**Data:** 1 de novembro de 2026  
**Projeto auditado:** KAIRIS  
**Diretório:** `C:\Users\eso41\OneDrive\Documentos\Protocolo EDGE\kairis_protocol`  
**Revisão atual:** `30eeb7b` (`main`) — *Add large EIS validation corpus*  
**Comparação principal:** revisão inicial `3586dd3` até `30eeb7b`  
**Documento anterior preservado:** `AUDITORIA_KAIRIS.md`  

Este documento é uma nova auditoria separada. Ele registra o que mudou desde a
implementação inicial, o que foi verificado no estado atual e o que ainda precisa
ser demonstrado antes de apresentar o KAIRIS como protocolo científico validado.
Ele não substitui validação metrológica, revisão por pares nem avaliação por
especialistas em eletroquímica.

## 1. Resumo executivo

O KAIRIS evoluiu de um pipeline local de cinco agentes para uma plataforma que
também possui:

- memória persistente e limitada por orçamento de contexto para o orquestrador;
- acionamento da LLM durante execução única e modo contínuo;
- atualização automática conservadora por Git;
- coleta de feedback humano e geração de dataset supervisionado;
- corpus versionado de 198 espectros sintéticos e públicos;
- manifestos, atribuição, hashes e evidência de execução do corpus;
- testes adicionais para essas funcionalidades.

O estado atual é tecnicamente consistente: o repositório estava limpo no início
da auditoria, os módulos Python compilaram, o arquivo de configuração satisfez o
schema e os **38 testes automatizados passaram**.

O corpus contém **198 entradas carregáveis**, e existem no disco 198 JSONs
consolidados, 198 relatórios HTML e 594 SVGs. O registro de validação informa zero
falhas de pipeline. Entretanto, isso demonstra principalmente compatibilidade de
entrada e robustez operacional. Ainda não demonstra acurácia científica dos
resultados de DRT, GSF e ESC.

Há também uma ressalva importante de proveniência: os 198 JSONs existentes foram
gerados na revisão `8a5c37f`, com `kairis_git_dirty=true`, enquanto o código atual
está na revisão `30eeb7b`. Na verificação registrada, 153 amostras foram
reutilizadas e somente 45 aparecem como processadas naquela chamada. Portanto, o
lote atual não deve ser apresentado como uma reprodução limpa e integral da
revisão final até que seja reexecutado, sem reutilização, a partir de um commit ou
tag limpo.

## 2. Escopo e método da auditoria

Foram inspecionados:

- histórico e estado do repositório Git;
- diferenças entre os cinco commits existentes;
- configuração e JSON Schema;
- pipeline, agentes, motores científicos e painel web;
- memória da LLM, controles em tempo real e fallback determinístico;
- atualizador automático;
- fluxo de feedback supervisionado;
- composição, licenças, hashes e resultados do corpus de validação;
- instalação, dependências, Docker e portabilidade declarada;
- testes automatizados e artefatos gerados.

Verificações executadas nesta auditoria:

```text
git status --short --branch                         → limpo antes do novo relatório
git log --oneline                                   → 5 commits em main
python -m pytest -q                                 → 38 passed in 13.32s
python -m compileall ...                            → OK
validação de protocol_config.json pelo schema       → OK
setup_kairis.py --check                             → dependências OK no Windows
update_kairis.py --check                            → sem remoto origin configurado
auditoria dos manifestos e artefatos do corpus      → 198 entradas e relatórios
```

Não foram executados nesta rodada:

- novo processamento integral dos 198 espectros;
- build real da imagem Docker;
- testes em uma máquina Linux;
- avaliação científica manual dos relatórios;
- benchmark quantitativo contra outros solvers de DRT ou Lin-KK;
- medição de cobertura de código.

## 3. Linha do tempo das mudanças

| Commit | Data local | Mudança principal |
|---|---:|---|
| `3586dd3` | 2026-11-01 17:18 | Implementação inicial do KAIRIS |
| `f4e2f3f` | 2026-11-01 17:32 | Memória persistente da LLM e controles ao vivo |
| `520685a` | 2026-11-01 17:41 | Atualização automática segura por Git |
| `8a5c37f` | 2026-11-01 17:52 | Aprendizado supervisionado por pesquisadores |
| `30eeb7b` | 2026-11-01 18:15 | Corpus amplo de validação EIS |

Entre a implementação inicial e a revisão atual foram alterados ou acrescentados
244 arquivos, com 26.408 inserções e 39 remoções. A maior parte do volume vem dos
espectros, metadados e fontes públicas incorporados ao corpus, não de código.

O estado atual possui 35 arquivos Python versionados e aproximadamente 4.284
linhas Python, incluindo aplicação, scripts e testes.

## 4. Mudança 1 — memória persistente e controle da LLM

### Implementação acrescentada

Foram adicionados `core/memory_store.py` e `core/runtime_control.py`, além de
integração em `agents/agent5_orchestrator.py`, `run_pipeline.py` e `web_app.py`.

A memória:

- grava conclusões em `output/memory/kairis_memory.json`;
- mantém o histórico completo no arquivo;
- seleciona somente os registros recentes que cabem nos limites
  `llm_memory_recent_records` e `llm_memory_max_prompt_chars`;
- usa escrita atômica;
- é opcional e não impede o funcionamento por regras.

O controle da LLM:

- pode ser definido por `--llm` ou `--no-llm` na linha de comando;
- pode ser relido antes de cada amostra por `--llm-control`;
- pode ser ligado ou desligado no painel web;
- afeta a próxima amostra quando o modo contínuo já está ativo;
- persiste o estado em `runtime_control.json` com escrita atômica.

### Estado observado

- A memória do diretório principal contém 6 registros.
- A memória usada na validação do corpus contém 201 registros para 198 amostras,
  indicando que algumas entradas foram acrescentadas novamente em reexecuções.
- A seleção para prompt é limitada, mas o histórico em disco cresce sem política
  de compactação ou deduplicação.

### Interpretação

Essa implementação fornece memória operacional, mas não equivale a memória
semântica nem a treinamento do modelo. A recuperação é baseada nos registros mais
recentes, não em similaridade entre sistemas eletroquímicos. Para uso científico,
o conteúdo da memória deve ser considerado contexto auxiliar e não evidência.

## 5. Mudança 2 — atualização automática segura

### Implementação acrescentada

Foi criado `update_kairis.py`. O atualizador:

- consulta remoto e branch configurados;
- recusa atualização se houver alterações locais versionadas;
- usa `fetch` seguido de `merge --ff-only`;
- recusa históricos divergentes;
- preserva a versão local quando a rede falha;
- registra o estado em `output/update_status.json`;
- instala `requirements.lock` somente quando o lock mudou e essa opção está
  habilitada;
- possui testes para fast-forward e recusa de checkout modificado.

Também foram integradas chamadas opcionais aos scripts de início para Windows e
Linux. As preferências locais podem ficar em `config/local_config.json`, ignorado
pelo Git, evitando alteração direta do arquivo versionado.

### Estado observado

- `auto_update_enabled` está `false` no arquivo de configuração atual.
- O repositório local não possui remoto Git configurado.
- `update_kairis.py --check` retornou `no_remote` para `origin/main`.

### Conclusão operacional

A funcionalidade existe e tem comportamento conservador, mas **não está
operacional nesta cópia**. Para distribuí-la a pesquisadores será necessário
publicar o repositório, configurar `origin` e decidir explicitamente se a
atualização automática deve ser habilitada. Para publicação científica, versões
usadas em experimentos devem permanecer presas a uma tag ou commit, mesmo que a
instalação cotidiana possa receber atualizações.

## 6. Mudança 3 — feedback e aprendizado supervisionado

### Implementação acrescentada

Foi criado `core/training_feedback.py` e acrescentada uma interface de revisão ao
painel. O pesquisador pode marcar uma interpretação como:

- `approved` — usa a resposta original da LLM;
- `corrected` — usa somente a correção escrita pelo pesquisador;
- `rejected` — mantém a auditoria, mas exclui a amostra do dataset de treino.

O sistema:

- mantém o histórico em `output/training/feedback.json`;
- gera `output/training/dataset.jsonl`;
- usa amostra e SHA-256 como identidade da revisão;
- preserva somente a revisão mais recente de cada identidade no dataset;
- incorpora até o número configurado de exemplos revisados nos prompts futuros;
- registra commit, resumo, regras, resposta original, correção e observações;
- escreve os arquivos atomicamente.

### Estado observado

No diretório de saída principal não há `feedback.json` nem `dataset.jsonl`.
Portanto:

- revisões humanas persistidas: **0**;
- exemplos supervisionados disponíveis: **0**;
- o limiar configurado de 50 exemplos para sinalizar prontidão não foi atingido.

### Limite importante

O fluxo implementado produz *in-context learning* imediato e um dataset para um
futuro experimento de SFT/LoRA. Ele não modifica pesos do Ollama e não executa
fine-tuning automático. O próprio `TRAINING.md` documenta corretamente essa
distinção.

Antes de treinar pesos, o dataset precisa de revisão científica, separação por
experimento, prevenção de vazamento e comparação contra regras determinísticas e
modelo-base.

## 7. Mudança 4 — corpus KAIRIS EIS Validation Corpus v1

### Composição verificada

O diretório `data/validation/kairis_eis_validation_v1` contém 198 entradas
diretamente carregáveis pelo KAIRIS:

| Origem | Quantidade | Papel declarado |
|---|---:|---|
| Sintéticos próprios do KAIRIS | 72 | desenvolvimento e validação |
| AutoECM publicado, sintético e rotulado | 45 | benchmark de treinamento |
| AutoECM publicado, sintético e rotulado | 27 | holdout publicado |
| Zenodo, células NMC811 21700 | 54 | avaliação externa experimental |
| **Total** | **198** | — |

Os 72 sintéticos próprios abrangem 12 famílias com seis variantes cada:

1. Randles RC;
2. ZARC/CPE;
3. duplo ZARC;
4. triplo ZARC;
5. Warburg semi-infinito;
6. difusão finita;
7. Gerischer;
8. modelo poroso/TLM;
9. adsorção indutiva;
10. indutância de cabos;
11. deriva não estacionária;
12. espectros esparsos com outliers.

Os dados AutoECM cobrem nove classes publicadas, com cinco exemplos de treino e
três de teste convertidos por classe. Os 54 espectros experimentais públicos vêm
do registro Zenodo 15422339 e representam células NMC811 em uma condição de 30%
de estado de carga.

### Integridade e atribuição

- O manifesto contém 198 linhas e SHA-256 por arquivo.
- O teste automatizado recalcula todos os hashes.
- Todos os 198 arquivos foram carregados pelo leitor durante os testes.
- A atribuição registra DOI, autores, origem e CC BY 4.0 para as fontes públicas.
- Os CSVs originais AutoECM permanecem junto das conversões.
- Os 54 CSVs Zenodo são preservados como arquivos públicos de origem.
- `synthetic_truth.csv` guarda parâmetros do gerador próprio.

### Alteração do leitor EIS

O leitor passou a aceitar CSV separado por vírgula e os aliases:

- `Frequency_Hz`;
- `Real_Ohm`;
- `Imag_Ohm`;
- `NegativeImaginary_Ohm`.

Isso permitiu ler diretamente os CSVs públicos acrescentados, sem eliminar o
suporte existente a tabulação, ponto e vírgula, vírgula decimal e cabeçalhos
BT-Lab.

## 8. Evidência operacional do corpus

O arquivo `validation_evidence/last_run_summary.json` registra:

| Indicador | Resultado |
|---|---:|
| Arquivos totais | 198 |
| Arquivos válidos para leitura | 198 |
| Arquivos inválidos | 0 |
| Amostras com os cinco agentes completos | 198 |
| Falhas registradas | 0 |
| Relatórios HTML presentes | 198 |
| JSONs consolidados presentes | 198 |
| SVGs presentes | 594 |
| LLM durante a validação | desativada |

Distribuição do registro de processamento:

| Estado | Quantidade |
|---|---:|
| Processado naquela chamada | 45 |
| Resultado existente reutilizado | 153 |

Resultados dos diagnósticos atuais:

| Origem | Total | Lin-KK válido | Concordância DRT–GSF | Divergência DRT–GSF |
|---|---:|---:|---:|---:|
| Experimental público | 54 | 54 | 0 | 54 |
| Sintético KAIRIS | 72 | 70 | 19 | 53 |
| Sintético publicado AutoECM | 72 | 70 | 50 | 22 |
| **Total** | **198** | **194** | **69** | **129** |

Os quatro casos com Lin-KK reprovado pertencem a duas variantes de deriva não
estacionária e a duas classes AutoECM. A divergência DRT–GSF é particularmente
frequente nas famílias de difusão, Gerischer, porosidade, indutância e no conjunto
experimental NMC811.

Esses números não devem ser classificados automaticamente como acertos ou erros.
DRT e GSF descrevem o espectro por critérios diferentes. As 129 divergências são
um conjunto de investigação científica que precisa de rótulos esperados e revisão
de especialistas.

## 9. Ressalva de proveniência da validação

Todos os 198 JSONs consolidados inspecionados registram:

```text
kairis_git_commit = 8a5c37fdae34bad48c304c41e52e0e0b96f7bfdc
kairis_git_dirty  = true
```

A revisão atual é `30eeb7b`. Além disso, a configuração registrada nos artefatos
não é idêntica à configuração atual. Por exemplo, os artefatos antigos registram
atualização automática habilitada, enquanto o arquivo atual a mantém desabilitada.

Consequências:

1. Os artefatos demonstram que uma versão de desenvolvimento processou o corpus.
2. Eles não constituem ainda uma execução congelada e limpa da versão atual.
3. A reutilização de 153 resultados impede afirmar que a última chamada recalculou
   integralmente os 198 espectros.
4. Para o artigo, o lote deve ser executado em diretório de saída novo ou com
   `--overwrite`, após criar uma tag limpa, e seus hashes devem ser arquivados.

Esta auditoria não reprocessou o lote porque o objetivo foi inspecionar o estado e
preservar os resultados existentes.

## 10. Testes automatizados

### Resultado atual

```text
38 passed in 13.32s
```

Há 10 arquivos de testes Python. A cobertura funcional inclui:

- identificação de eletrólito e cálculo geométrico de Z₀_G4;
- fallback de Z₀_G4 para R∞;
- aceitação e rejeição básica por Lin-KK;
- formatos heterogêneos de entrada EIS;
- terminologia Spectral Smoothness;
- escrita atômica e JSON estrito;
- validação de configuração por schema;
- política `--overwrite`;
- controle da LLM por amostra;
- memória persistente com contexto limitado;
- cache D3 inline;
- proveniência consolidada;
- seleção de modelos por memória RAM;
- Ollama e fallback por regras;
- feedback humano e reconstrução do dataset;
- atualizador Git;
- integridade e leitura das 198 entradas;
- execução de ponta a ponta pelo painel web.

### Lacunas de teste

- `synthetic_truth.csv` ainda não é comparado automaticamente com resultados
  numéricos de DRT, GSF ou ESC.
- Não existem tolerâncias científicas congeladas por família de espectro.
- Não há benchmark automatizado contra solvers externos.
- Não há cobertura de código publicada.
- Os scripts JavaScript de verificação visual não fazem parte do `pytest` padrão.
- Não existe matriz CI demonstrada para Windows, Linux e Docker.
- A imagem Docker não foi construída nesta auditoria.

## 11. Infraestrutura e portabilidade atuais

### Pontos confirmados

- Python 3.12.14 foi detectado no Windows usado nesta auditoria.
- Foram detectados 15,9 GB de RAM.
- As dependências Python instaladas foram consideradas válidas pelo assistente.
- Ollama foi encontrado localmente.
- O Dockerfile usa usuário não-root `kairis`.
- O contêiner desativa LLM por padrão.
- Ollama externo pode ser acessado por `host.docker.internal`.
- JSON, HTML e SVG usam escrita temporária, `flush`, `fsync` e `os.replace` nos
  caminhos normais de geração de artefatos.
- A configuração possui schema com chaves obrigatórias, tipos e limites.
- As dependências diretas estão separadas das dependências de desenvolvimento.
- Existe `requirements.lock` para reprodução de ambiente.

### Pontos não demonstrados nesta rodada

- funcionamento em uma distribuição Linux real;
- build limpo e healthcheck da imagem Docker;
- compatibilidade do lock em todas as plataformas pretendidas;
- funcionamento em máquinas reais de 4 GB e 8 GB;
- instalação automatizada de Python/Ollama em cada sistema suportado.

## 12. Painel web e segurança

O painel atualmente oferece:

- upload de `.txt` e `.csv`;
- execução única;
- modo contínuo;
- acompanhamento dos cinco agentes;
- ativação e desativação da LLM;
- abertura de relatórios;
- aprovação, correção ou rejeição de interpretação;
- download do dataset supervisionado;
- interrupção da execução.

A aplicação local inicia por padrão em `127.0.0.1`, o que é apropriado para uso
individual. Porém, não existe autenticação, autorização, proteção CSRF nem
isolamento por usuário. O Compose publica `8000:8000`, podendo expor o painel em
interfaces de rede do computador hospedeiro.

Consequentemente, o painel deve continuar restrito ao computador local. Uma
implantação em laboratório compartilhado exige autenticação, política de origem,
limites operacionais e revisão de segurança.

## 13. Configuração atual

O arquivo atual define, entre outros pontos:

- protocolo oficial `KAIRIS`;
- Lin-KK com até 50 elementos RC e limiares explícitos;
- 100 pontos na malha de DRT;
- geometria de célula e tabela de condutividade;
- Ollama como provedor padrão;
- `gemma3:4b` como modelo configurado;
- perfis leves por RAM, incluindo `gemma3:1b` e Qwen3 4B quantizado;
- fallback por regras ativado;
- memória persistente ativada;
- fluxo supervisionado ativado;
- D3 via CDN por padrão e opção inline;
- atualização automática desativada;
- parâmetros ainda sem efeito isolados em `_reserved_not_yet_implemented`.

O schema atual foi validado com sucesso. As substituições por ambiente permitem
desativar a LLM no contêiner e alterar URL/modelo do Ollama.

## 14. Achados priorizados

### Prioridade crítica para o artigo científico

1. **Acurácia científica ainda não foi quantificada.** O corpus confirma leitura
   e execução, mas os testes não comparam resultados aos parâmetros conhecidos do
   gerador nem a referências independentes.

2. **A execução dos 198 espectros não corresponde a uma revisão limpa atual.** Os
   artefatos registram commit anterior e árvore modificada; 153 resultados foram
   reutilizados. É necessário gerar um lote reproduzível após taguear a versão.

3. **As 129 divergências DRT–GSF precisam de interpretação planejada.** Todas as
   54 amostras experimentais divergem pela regra atual. Isso pode revelar diferença
   entre os observáveis, inadequação dos limiares ou baixa transferibilidade; não é
   possível escolher entre essas hipóteses sem validação independente.

4. **O corpus experimental é estreito.** Há 54 células, mas todas pertencem ao
   mesmo tipo e condição declarada. Ainda faltam fontes externas independentes de
   corrosão, supercapacitores, sensores, células a combustível e outros sistemas.

### Prioridade alta de engenharia e governança

5. **A atualização automática não funciona nesta cópia**, pois não há remoto e a
   opção está desativada. Isso é seguro no estado atual, mas precisa ser resolvido
   antes da distribuição.

6. **O painel não deve ser exposto à rede sem proteção.** A configuração local é
   segura por loopback, enquanto o Compose deve ser restringido ou protegido.

7. **O aprendizado supervisionado ainda não possui dados reais revisados.** A
   infraestrutura existe, mas o diretório principal contém zero exemplos. Não se
   deve afirmar que a LLM foi treinada ou melhorada até executar e avaliar esse
   processo.

8. **Falta uma matriz de reprodução multiplataforma.** O teste atual ocorreu no
   Windows. Linux e Docker continuam documentados, mas não foram comprovados nesta
   auditoria.

### Prioridade média

9. A memória completa cresce indefinidamente e pode acumular registros repetidos.
   Convém deduplicar por hash/versão e oferecer arquivamento.

10. A LLM continua produzindo texto livre. O fallback funciona, mas falta um
    verificador estruturado das afirmações geradas.

11. O painel deriva progresso do log textual. Um manifesto estruturado por lote
    facilitaria auditoria, retomada e comparação entre execuções.

12. O atualizador confia no remoto Git configurado. Para distribuição científica,
    recomenda-se usar releases assinadas ou, no mínimo, tags imutáveis e hashes.

## 15. Mudanças que resolveram problemas anteriores

Em relação ao estado inicial, estão implementados e testados:

- `numpy.trapz` compatível com NumPy 1.x e fallback para versões que removeram o
  alias;
- cálculo geométrico de Z₀_G4 quando o eletrólito é identificado;
- fallback documentado para R∞;
- separação entre Spectral Smoothness e validação Lin-KK verdadeira;
- proveniência por amostra, incluindo SHA-256, versões, configuração e commit;
- escrita atômica dos artefatos;
- configuração validada por JSON Schema;
- política explícita de reprocessamento;
- D3 inline opcional;
- contêiner sem root;
- nomes de saída resistentes a colisões em subpastas;
- painel web local;
- instalação e inicialização multiplataforma;
- memória e controles da LLM;
- atualização automática conservadora;
- feedback humano e dataset supervisionado;
- corpus amplo, manifestos e atribuição pública.

## 16. Recomendações imediatas

Ordem recomendada antes de usar o corpus no manuscrito:

1. Criar uma tag candidata, por exemplo `v1.0.0-rc1`, com árvore Git limpa.
2. Executar os 198 espectros em um diretório novo, com LLM desativada, sem
   reaproveitar artefatos anteriores.
3. Arquivar configuração, log, manifestos, hashes e versão do ambiente junto do
   lote.
4. Criar testes de regressão numérica usando `synthetic_truth.csv`, com tolerâncias
   definidas antes de analisar os resultados.
5. Avaliar separadamente as 129 divergências, com revisão cega por especialistas.
6. Acrescentar pelo menos um conjunto experimental de outro laboratório ou outra
   família eletroquímica.
7. Configurar o remoto oficial, mas manter atualizações desligadas nas execuções
   científicas congeladas.
8. Rodar a mesma tag em Windows, Linux e Docker e comparar hashes das métricas.
9. Iniciar a revisão humana das interpretações somente com protocolo de anotação e
   divisão de dados previamente definidos.
10. Publicar versão, código, manifesto e dados permitidos com DOI e instrução de
    reprodução de um comando.

## 17. Conclusão

O KAIRIS está mais completo, rastreável e operacional do que na implementação
inicial. As atualizações de memória, controle da LLM, atualização por Git, feedback
supervisionado e corpus de 198 espectros são mudanças reais, integradas ao sistema
e cobertas por testes.

O principal gargalo deixou de ser a construção do pipeline. Agora é a demonstração
de validade científica: métricas contra verdades conhecidas, validação externa
diversa, análise das divergências, execução limpa da versão congelada e reprodução
independente.

No estado auditado, o KAIRIS pode ser descrito com segurança como uma plataforma
funcional e reprodutível de análise exploratória e geração de relatórios. Ainda não
há evidência suficiente para afirmar que todas as classificações ou parâmetros
produzidos constituem identificação científica validada de mecanismos
eletroquímicos.
