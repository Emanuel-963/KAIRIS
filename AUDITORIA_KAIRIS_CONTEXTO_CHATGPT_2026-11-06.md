# Auditoria informativa e contexto operacional do KAIRIS

**Data da auditoria:** 6 de novembro de 2026  
**Finalidade:** permitir que uma nova conversa com o ChatGPT compreenda o projeto
sem depender do histórico das conversas anteriores.  
**Escopo auditado:** repositório integrado, worktrees independentes de GSF/RSF e
ESC, evidência retrospectiva, validação externa bloqueada, manuscrito e
infraestrutura.  
**Natureza:** retrato informativo do estado atual; não substitui os planos
científicos congelados nem autoriza a abertura da análise confirmatória.

---

## 1. Resumo executivo

KAIRIS significa **Kramers–Kronig-Assessed Impedance, Relaxation, and Integrated
Spectroscopy**. É um protocolo e software aberto de análise multiperspectiva de
espectroscopia de impedância eletroquímica (EIS). O fluxo integrado é:

```text
arquivo EIS
   ↓
Agente 1 — importação, suavidade local e Lin-KK
   ↓
Agente 2 — DRT, R∞ e referências Z₀
   ↓
Agente 3 — GSF
   ↓
Agente 4 — ESC
   ↓
Agente 5 — síntese determinística, proveniência, JSON e HTML
```

O projeto está funcional, testado, portável e possui painel web. O corpus
retrospectivo de 198 espectros foi processado integralmente, e os gates
matemáticos dos módulos independentes passaram. Isso demonstra robustez de
engenharia, recuperação em referências sintéticas simples, equivalência modular
e invariantes matemáticos. **Ainda não demonstra identificação causal automática
de mecanismos eletroquímicos.**

A validação externa confirmatória usa 42 espectros experimentais de aço
inoxidável e está propositalmente bloqueada. A especificação científica, o código
e a tag foram congelados, mas faltam os aceites privados dos revisores e o
registro OSF. Nenhum agente KAIRIS foi executado nesses 42 casos.

## 2. Alegação científica atual

A formulação defensável do artigo principal é:

> KAIRIS é um protocolo reprodutível de análise multiperspectiva de EIS que
> integra admissibilidade espectral, DRT, GSF e ESC, quantifica concordâncias e
> divergências entre observáveis e se abstém quando a evidência é insuficiente.

O projeto **não deve**, no estado atual, ser descrito como:

- identificador automático de mecanismos eletroquímicos verdadeiros;
- solucionador de um circuito equivalente único;
- prova de que toda divergência DRT–GSF representa erro;
- validação causal de GSF ou ESC apenas porque os gráficos são regulares;
- sistema cuja interpretação científica depende de uma LLM.

## 3. Repositórios, branches e estado Git

### 3.1 Protocolo integrado

- diretório: `kairis_protocol`;
- branch: `main`;
- HEAD auditado: `340253a` — `Record external validation freeze identity`;
- remoto: `https://github.com/Emanuel-963/KAIRIS.git`;
- estado: árvore limpa no momento da auditoria;
- diferença para `origin/main`: branch local quatro commits à frente;
- tag retrospectiva: `validation-plan-v1.0`;
- tag confirmatória local: `external-validation-plan-v1.0`;
- commit científico apontado pela tag confirmatória:
  `94a03c366b0d26ec8f2e05befed0660fb2ff0f1d`.

Os quatro commits novos da `main` e a tag confirmatória ainda não haviam sido
enviados ao GitHub na data desta auditoria.

### 3.2 GSF/RSF independente

- worktree: `../kairis-gsf-standalone`;
- branch: `standalone/gsf`;
- HEAD: `b3d9965` — `Develop experimental RSF framework and sampling study`;
- estado: limpa e dois commits à frente de `origin/standalone/gsf`;
- teste nesta auditoria: **69 aprovados**.

Essa branch contém o comando GSF independente e um framework experimental RSF,
formalização v0.1, protocolo de validação, estudo de amostragem e rascunho de
artigo metodológico. Esse material é uma linha científica paralela; não deve ser
silenciosamente mesclado à análise confirmatória já congelada da `main`.

### 3.3 ESC independente

- worktree: `../kairis-esc-standalone`;
- branch: `standalone/esc`;
- HEAD: `67076b9` — `Develop ESC scientific validation framework`;
- estado: limpa e dois commits à frente de `origin/standalone/esc`;
- teste nesta auditoria: **71 aprovados**.

Essa branch contém referências ESC explícitas, plano científico próprio,
validação algébrica/física, busca de anterioridade e rascunho de artigo. ESC
significa oficialmente **Electrochemical Spectral Cartography**. A transformação
bilinear utilizada é a transformação clássica de Smith; a originalidade proposta
está nas referências eletroquímicas, descritores, regras de interpretação e
abstenção, não na transformação matemática.

## 4. Arquitetura do protocolo integrado

### Agente 1 — `agents/agent1_eis_reader.py`

- importa `.txt` e `.csv` por conteúdo e cabeçalhos;
- reconhece decimal por vírgula ou ponto, diferentes separadores e convenções de
  `Im(Z)`/`-Im(Z)`;
- remove pontos inválidos e frequências duplicadas de forma determinística;
- calcula `smoothness_residue_pct`, indicador de suavidade local;
- executa Lin-KK verdadeiro em `core/lin_kk_validator.py`;
- mantém explícito que suavidade local não é validação integral de
  Kramers–Kronig.

### Agente 2 — `agents/agent2_drt.py`

- resolve DRT não negativa por Tikhonov em `core/drt_solver.py`;
- usa grade de tempos de relaxação e seleção por curvatura da L-curve;
- reporta picos, áreas, separação e confiabilidade da resolução;
- preserva R∞ bruto e se abstém quando a borda de alta frequência não forma platô
  suficiente;
- oferece extrapolação assintótica apenas como resultado secundário;
- produz referências `Z0_G1` a `Z0_G4`;
- para G4, usa `L/(κA)` quando o eletrólito é reconhecido pelo nome do arquivo e
  existe no banco de condutividades; caso contrário, registra fallback.

### Agente 3 — `agents/agent3_gsf.py`

- calcula o **Golden Spectral Field (GSF)** em `core/gsf_engine.py`;
- normaliza os componentes espectrais;
- produz `q`, `alpha`, `kphi`, gradiente, `I_crit`, `f_Icrit` e regime GSF;
- deve ser interpretado como uma visão espectral global complementar, não como
  verdade mecanística isolada.

### Agente 4 — `agents/agent4_esc.py`

- executa **Electrochemical Spectral Cartography (ESC)** em
  `core/esc_engine.py`;
- aplica a transformação de Smith para quatro referências Z₀ registradas;
- preserva frequência, Γ, centróide, média de `|Γ|`, ponto de baixa frequência e
  flags;
- permite zoom/pan no relatório, mas geometria visual não escolhe automaticamente
  um mecanismo.

### Agente 5 — `agents/agent5_orchestrator.py`

- consolida os quatro módulos;
- aplica regras determinísticas antes de qualquer LLM;
- reconhece o padrão `diffusion_dominated` + `pseudocapacitive` como
  `intercalation_pseudocapacitive`, sem flag automática de inconsistência;
- preserva desacordos, resultados inconclusivos e abstenções;
- grava JSON consolidado e relatório HTML;
- inclui SHA-256 da entrada, timestamp, versões das bibliotecas, commit Git,
  estado da árvore e configuração efetiva sem segredos.

## 5. Relatório e visualização

O relatório do Agente 5 é um HTML único com dados JSON embutidos:

- D3.js: Nyquist, Bode, DRT, quatro grupos ESC e mapa q do GSF;
- tooltip de frequência por ponto;
- zoom e pan em Nyquist e ESC;
- tooltip de picos DRT com τ, γ máximo e área;
- Matplotlib somente para SVGs estáticos de `alpha(f)`, `kphi(f)` e gradiente;
- D3 por CDN por padrão;
- opção `report_d3_inline=true` para usar o bundle local em
  `web/static/d3.min.js`;
- proveniência em seção recolhível no rodapé.

JSON, SVG e HTML são gravados atomicamente: temporário no mesmo diretório,
`flush`, `fsync` e `os.replace`.

## 6. Operação, painel e portabilidade

Entradas principais:

```bash
python run_pipeline.py --input data/input --output output
python run_pipeline.py --input data/input --output output --watch
python web_app.py --no-open
```

O painel local usa Flask e normalmente abre em `http://127.0.0.1:8000`. Ele
permite upload, execução, monitoramento, visualização dos agentes, abertura dos
relatórios, controle da LLM e feedback humano.

Características de infraestrutura já implementadas:

- Windows, Linux e macOS;
- scripts PowerShell e shell;
- instalador assistido e detecção de Python/Ollama;
- downloads de Ollama e modelos sempre opcionais e confirmados;
- perfis de modelo para 4 GB, 8 GB e 16 GB+;
- Docker sem root e Ollama externo opcional;
- configuração validada por JSON Schema;
- `requirements.lock` para reprodução;
- atualização Git somente por fast-forward e somente quando autorizada;
- política `--overwrite`: resultados existentes são preservados por padrão;
- nomes de saída incluem o caminho relativo para evitar colisões;
- funcionamento determinístico sem LLM.

Ambiente verificado em 6 de novembro de 2026:

- Windows 10;
- Python 3.12.14;
- 15,9 GB de RAM;
- dependências Python: OK;
- Ollama localizado no computador;
- testes da `main`: **71 aprovados em 23,46 s**.

## 7. LLM, memória e aprendizado

A interpretação por Ollama é opcional. O pipeline científico não depende dela.
No `protocol_config.json`, a interface geral pode estar com `llm_enabled=true`,
mas o executor confirmatório força:

```json
{
  "llm_enabled": false,
  "llm_memory_enabled": false,
  "supervised_learning_enabled": false
}
```

No uso comum:

- a memória estruturada fica em `output/memory/kairis_memory.json`;
- somente uma janela limitada de registros entra no prompt;
- feedback aprovado/corrigido gera `output/training/dataset.jsonl`;
- exemplos validados podem ser usados como few-shot;
- fine-tuning real não ocorre silenciosamente e não deve usar o conjunto de
  teste confirmatório.

Uma futura conversa não deve chamar few-shot, memória persistente ou feedback
humano de “treinamento dos pesos” sem que um fine-tuning separado tenha sido
realmente executado.

## 8. Corpus retrospectivo de 198 espectros

Composição:

| Origem | Quantidade | Papel |
|---|---:|---|
| sintéticos KAIRIS | 72 | desenvolvimento, recuperação e robustez |
| sintéticos publicados AutoECM | 72 | benchmark retrospectivo |
| experimentais públicos NMC811 | 54 | avaliação experimental retrospectiva |
| **total** | **198** | corpus conhecido, não confirmatório |

Evidência registrada em 1º de novembro de 2026:

- 198 arquivos válidos de 198;
- 198 processados;
- zero falhas;
- LLM desativada;
- 129 divergências DRT–GSF preservadas no relatório.

A release de desenvolvimento encontrou 198 JSONs e 198 HTMLs e aprovou todos os
gates configurados. Para seis Randles simples:

- Lin-KK: 100%;
- um pico DRT: 100%;
- erro relativo mediano de R∞: aproximadamente 0,226%;
- pior erro relativo de R∞: aproximadamente 0,819%;
- erro mediano de `log10(tau)`: aproximadamente 0,0346 década;
- pior erro de `log10(tau)`: aproximadamente 0,0346 década.

Esses resultados são desenvolvimento retrospectivo no commit antigo
`05b85d1`; não são resultados confirmatórios da versão atual.

## 9. Gates independentes GSF e ESC

O relatório retrospectivo H3–H6 avaliou os 198 espectros e obteve 100% em:

- importação suportada;
- equivalência GSF integrado/independente;
- invariância de escala do GSF;
- completude de artefatos GSF;
- equivalência ESC integrado/independente;
- consistência da inversão ESC;
- limite matemático de passividade quando aplicável;
- completude de artefatos ESC.

Essa evidência foi gerada com `main` em `14fe233`, GSF em `26c50e1` e ESC em
`311f0c0`. As branches independentes avançaram depois disso; portanto, o relatório
não deve ser apresentado como validação automática de todas as funcionalidades
científicas adicionadas nos commits atuais `b3d9965` e `67076b9`.

## 10. Validação externa confirmatória de 42 espectros

### Fonte e preparação

- conjunto: aço inoxidável 316L em NaCl 0,1 M;
- 42 espectros;
- 36 frequências por espectro, de 0,01 Hz a 100 kHz;
- dez subgrupos de origem;
- DOI do repositório: `10.17605/OSF.IO/XRAV8`;
- DOI do dataset: `10.17632/r9snmwyzkv.1`;
- licença: CC BY 4.0;
- arquivo canônico SHA-256:
  `01c85092b46a68a832124d7327157b6327a0d440ea3b66ba277694432edfb8b3`;
- 42 CSVs cegos preparados e com hashes verificados;
- chave caso–condição mantida em diretório privado ignorado pelo Git.

### Pergunta e endpoints congelados

**P1 — integridade:** os 42 casos devem concluir, possuir JSON/HTML, hash e
proveniência corretos, sem artefatos parciais ou falhas silenciosas.

**P2 — concordância de resposta dominante:** comparação entre o mapeamento
determinístico KAIRIS e o consenso exato pré-adjudicação de Reviewer A e Reviewer
B, nas classes `kinetic`, `diffusive`, `pseudocapacitive` e `mixed`.

O estudo é de estimação. Não existe limiar mínimo de acurácia inventado para os
42 casos. Serão relatados macro-F1, balanced accuracy, métricas por classe,
matriz de confusão, abstenção e IC de 95% por bootstrap dos dez subgrupos.

Mapeamento principal congelado:

| DRT | GSF | Classe P2 |
|---|---|---|
| `kinetic_dominated` | `resistive` | `kinetic` |
| `diffusion_dominated` | `diffusive` | `diffusive` |
| `diffusion_dominated` | `pseudocapacitive`, com diagnóstico especial | `pseudocapacitive` |
| `mixed` | `mixed` | `mixed` |
| qualquer combinação não mapeada | qualquer | `undetermined` |

Lin-KK inválido, falha de módulo, inconsistência genérica ou combinação não
mapeada obriga abstenção. A abstenção KAIRIS permanece no denominador; ausência
de consenso humano é relatada separadamente.

GSF possui cinco descritores secundários pré-fixados. ESC G1–G3 é descritiva;
G4 foi excluído dos contrastes científicos porque a fonte não fornece geometria
específica suficiente da célula de pasta.

### Estado do intertravamento

Na auditoria, sete gates passavam:

- especificação científica;
- hash da fonte;
- manifesto cego e 42 hashes;
- materiais dos revisores;
- identidade congelada de código/configuração;
- tag imutável;
- árvore Git limpa.

Três gates permaneciam bloqueados:

1. aceites, prazo e declarações de conflito no arquivo privado;
2. registro OSF público ou sob embargo;
3. desbloqueio explícito do coordenador depois da verificação do registro.

Comando obrigatório para conferir:

```bash
python scripts/check_external_validation_readiness.py
```

Enquanto retornar `analysis_lock: locked`, **não executar**
`scripts/run_external_validation.py` e não tentar contornar o verificador.

## 11. Avaliação humana e privacidade

O repositório público usa apenas:

- `Reviewer A`;
- `Reviewer B`;
- `Reviewer R`.

As identidades, afiliações, ORCIDs, relações e declarações ficam exclusivamente
no registro privado do coordenador. O usuário proibiu expressamente publicar
essas informações no repositório. Uma conversa futura não deve inserir nomes de
avaliadores em README, artigo, commits, issues, relatórios públicos ou arquivos
versionados sem nova autorização explícita.

Reviewer A e B analisam todo o conjunto de modo independente. Reviewer R atua
como substituto ou adjudicador, nunca nas duas funções na mesma rodada. A
concordância é calculada antes da adjudicação, e o desacordo original é
preservado.

## 12. Manuscrito e estratégia editorial

- periódico principal: **Electrochimica Acta**;
- alternativa: **Journal of Electroanalytical Chemistry**;
- tipo: artigo científico completo;
- template: Elsevier CAS single-column;
- fonte principal: `paper/manuscript_electrochimica_acta/main.tex`;
- estado: Introdução, perguntas científicas e parte substancial dos Métodos já
  redigidos; resultados confirmatórios permanecem como placeholders;
- tamanho observado: 411 linhas de LaTeX;
- PDF local existente: aproximadamente 292 kB;
- meta de submissão científica: **16 de fevereiro de 2027**;
- pacote JOSS: preparar até essa data e submeter na primeira data elegível,
  prevista para 3 de maio de 2027 ou depois.

O artigo principal deve enfatizar protocolo, validação e limites científicos. O
painel web, Docker e Ollama entram como reprodutibilidade/infraestrutura, não como
contribuição científica principal.

## 13. Anterioridade e nomenclatura

Documentos relevantes:

- `paper/PRIOR_ART_SEARCH_PROTOCOL_v1.md`;
- `paper/PRIOR_ART_GSF_RSF_v1.md`;
- `paper/PRIOR_ART_ESC_v1.md`.

Regras terminológicas:

- usar sempre **KAIRIS** para o protocolo;
- não usar nomes antigos do projeto;
- ESC significa somente **Electrochemical Spectral Cartography**;
- não atribuir novidade à transformação clássica de Smith;
- GSF deriva conceitualmente do campo RSF, mas hipóteses novas da branch
  independente não alteram retroativamente endpoints já congelados.

## 14. Riscos, lacunas e limitações atuais

1. A validação externa ainda não foi registrada nem executada.
2. As anotações cegas dos especialistas ainda não existem.
3. Lin-KK e DRT ainda precisam de comparadores externos estabelecidos no artigo.
4. Ablacões completas de GSF e ESC ainda precisam ser executadas e reportadas.
5. A análise de sensibilidade a regularização, ruído, truncamento e densidade de
   pontos ainda precisa ser consolidada para a submissão.
6. Falta reprodução integral por outra pessoa/máquina em Windows, Linux e macOS,
   incluindo perfis de 4 GB e 8 GB.
7. Os 129 desacordos DRT–GSF são resultado científico potencial, não uma lista de
   129 erros; precisam de taxonomia e análise agrupada.
8. As branches independentes possuem ciência nova posterior ao relatório H3–H6 e
   exigem validação própria antes de alegações fortes.
9. O repositório remoto está atrás dos três worktrees locais; isso é risco de
   perda até que commits e tags sejam enviados conscientemente.
10. A configuração geral permite LLM, mas qualquer execução científica primária
    deve provar no manifesto que LLM, memória e few-shot estavam desligados.

## 15. Próximos passos prioritários

### P0 — imediatamente

1. obter e arquivar privadamente os três aceites e declarações;
2. gerar o pacote cego e entregá-lo sem chave ou resultados KAIRIS;
3. registrar adendo, configuração, hashes, commit e materiais no OSF;
4. criar o registro público do OSF a partir de
   `paper/EXTERNAL_VALIDATION_REGISTRATION_TEMPLATE.json`;
5. executar novamente o verificador de prontidão;
6. somente após o desbloqueio, executar os 42 espectros sem LLM;
7. receber e congelar os dois formulários independentes;
8. calcular concordância e análise confirmatória com os scripts versionados.

### P0 — em paralelo, sem tocar o conjunto confirmatório

1. concluir comparador Lin-KK independente;
2. concluir comparador DRT independente;
3. definir e executar ablações do pipeline;
4. consolidar benchmark de robustez e sensibilidade;
5. preparar reprodução limpa multiplataforma;
6. continuar Introdução/Métodos e preparar esqueletos de tabelas/figuras sem
   preencher resultados inexistentes.

### P1 — depois dos resultados congelados

1. análise dos desacordos e domínio de validade;
2. reprodução independente final;
3. tabelas, figuras, suplemento e discussão;
4. release `v1.0.0`, Zenodo/DOI e pacote FAIR;
5. submissão a Electrochimica Acta;
6. preparação/submissão JOSS quando elegível;
7. continuidade dos artigos independentes GSF/RSF e ESC.

## 16. Comandos úteis e seguros

### Estado e testes

```powershell
git status
git log --oneline --decorate -10
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe setup_kairis.py --check
```

### Prontidão confirmatória — somente leitura

```powershell
.\.venv\Scripts\python.exe scripts\check_external_validation_readiness.py
```

### Pacote cego — permitido antes da análise KAIRIS

```powershell
.\.venv\Scripts\python.exe scripts\build_external_review_pack.py `
  --destination output\external_review_pack_v1
```

### Execução confirmatória — proibida enquanto bloqueada

```powershell
.\.venv\Scripts\python.exe scripts\run_external_validation.py `
  --output output\external_validation_316l_v1
```

O último comando só pode ser usado quando o verificador retornar
`ready_for_scientific_analysis: true`.

## 17. Hierarquia documental para uma nova conversa

Quando houver conflito ou dúvida, consultar nesta ordem:

1. `config/external_validation_plan_v1.json` para decisões confirmatórias
   executáveis;
2. `paper/EXTERNAL_VALIDATION_FREEZE_RECORD.json` para commit e hashes;
3. `paper/EXTERNAL_VALIDATION_ADDENDUM_v1.md` para justificativa científica;
4. `paper/VALIDATION_PLAN_v1.md` para o plano retrospectivo H1–H6;
5. `config/protocol_config.json` e `config/protocol_schema.json` para parâmetros;
6. código e testes para o comportamento efetivamente implementado;
7. esta auditoria apenas como mapa informativo.

O README explica uso, mas não substitui os arquivos científicos congelados.
Relatórios antigos em `output/` documentam commits antigos e não devem ser
atribuídos automaticamente ao HEAD atual.

## 18. Instruções de continuidade para o ChatGPT

Ao iniciar uma nova conversa sobre o KAIRIS:

1. ler este arquivo e os documentos congelados relevantes;
2. executar `git status` antes de editar;
3. preservar alterações do usuário e dos outros worktrees;
4. não reprocessar os 42 espectros externos enquanto o gate estiver bloqueado;
5. não publicar identidades dos avaliadores;
6. não tratar 198/198 como prova causal;
7. distinguir resultados retrospectivos, confirmatórios e exploratórios;
8. manter KAIRIS funcional sem Ollama;
9. registrar qualquer mudança posterior ao congelamento no log de desvios;
10. nunca alterar endpoint, limiar ou exclusão depois de ver resultados sem
    declará-lo como desvio.

Uma boa primeira verificação é:

```powershell
git status
.\.venv\Scripts\python.exe scripts\check_external_validation_readiness.py
.\.venv\Scripts\python.exe -m pytest -q
```

---

## 19. Conclusão da auditoria

O KAIRIS já ultrapassou o estágio de protótipo funcional: possui arquitetura
modular, testes, corpus retrospectivo, proveniência, painel, portabilidade,
branches independentes e manuscrito em andamento. O principal gargalo atual não
é adicionar módulos. É concluir, sem vazamento e sem flexibilização posterior,
o registro OSF, a avaliação humana cega, a execução externa bloqueada, os
comparadores científicos e a reprodução independente.

O estado correto em 6 de novembro de 2026 é:

> **software funcional e retrospectivamente validado; protocolo confirmatório
> congelado e tecnicamente pronto; análise externa ainda bloqueada e sem
> resultados KAIRIS.**
