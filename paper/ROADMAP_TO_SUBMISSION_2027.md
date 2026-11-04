# Roadmap prioritário do KAIRIS até a submissão científica

**Projeto:** KAIRIS — Kramers–Kronig-Assessed Impedance, Relaxation, and
Integrated Spectroscopy

**Versão do roadmap:** 1.0

**Data de referência:** 4 de novembro de 2026

**Meta de submissão do artigo científico:** 16 de fevereiro de 2027

**Meta JOSS:** pacote editorial pronto em 16 de fevereiro de 2027 e submissão na
primeira data elegível, prevista para **3 de maio de 2027 ou depois**

**Responsável científico:** pesquisador responsável pelo KAIRIS

## 1. Objetivo e regra de prioridade

O objetivo deste plano é converter o KAIRIS de um pipeline funcional e testado em
um protocolo cientificamente validado, reproduzível e submetível. Até 16 de
fevereiro de 2027, uma tarefa só entra no caminho crítico quando contribui
diretamente para pelo menos um destes resultados:

1. validação científica externa e prospectiva;
2. avaliação humana cega e reprodutível;
3. comparação com métodos de referência, ablações ou análise de sensibilidade;
4. evidência estatística compatível com as alegações do artigo;
5. reprodução independente em Windows, Linux e macOS;
6. manuscrito, suplemento, dados e software arquiváveis.

Novos módulos, treinamento de LLM, refinamentos cosméticos do painel e expansão
indefinida do corpus ficam fora do caminho crítico, salvo quando corrigirem uma
falha que impeça um dos seis resultados acima.

## 2. Estado de partida

### 2.1 Evidência já disponível

- plano retrospectivo/de desenvolvimento congelado na tag
  `validation-plan-v1.0`;
- hipóteses H1–H6 e critérios executáveis versionados;
- 198 espectros processados pelo corpus retrospectivo;
- gates H3–H6 executados automaticamente para GSF e ESC independentes;
- equivalência numérica integrada/independente e propriedades matemáticas
  aprovadas no corpus atual;
- testes automatizados em Windows, Ubuntu e macOS;
- instalação assistida, Docker, proveniência por amostra e operação sem LLM;
- branches autônomas `standalone/gsf` e `standalone/esc` congeladas.

### 2.2 Evidência ainda ausente ou incompleta

- conjunto confirmatório externo realmente não examinado;
- adendo prospectivo com tamanho amostral, origem e exclusões definidos;
- pré-registro do estudo confirmatório antes da abertura dos resultados;
- anotações cegas de pelo menos dois especialistas;
- comparações completas com implementações de referência;
- análise de ablação e sensibilidade pré-especificada;
- estimativas com intervalos de confiança e agrupamento correto;
- reprodução completa por pessoa/máquina não usada no desenvolvimento;
- manuscrito científico, suplemento e pacote arquivado com DOI;
- histórico público mínimo exigido para submissão ao JOSS.

O resultado de 198/198 e os gates H3–H6 demonstram robustez de engenharia,
equivalência modular e invariantes matemáticos. Eles não são, isoladamente,
evidência de identificação causal de mecanismos eletroquímicos.

## 3. Caminho crítico

```text
Definir estudo externo
        ↓
Congelar adendo + hashes + plano estatístico
        ↓
Registrar no OSF antes de abrir resultados
        ↓
Ingerir dados cegos ───────┬──── Avaliação humana cega
                           ├──── Baselines/ablações
                           └──── Execução KAIRIS sem LLM
                                      ↓
                           Desbloqueio e análise estatística
                                      ↓
                           Reprodução independente integral
                                      ↓
                        Release v1.0 + DOI + manuscrito
                                      ↓
                         Submissão em 16/02/2027
```

Qualquer atraso na obtenção do conjunto externo, no pré-registro ou na avaliação
dos especialistas ameaça diretamente a data final. Essas três atividades têm
precedência sobre novas funcionalidades.

## 4. Frentes de trabalho

### Frente A — validação externa confirmatória (P0)

**Objetivo:** testar as alegações principais em dados que não influenciaram o
desenvolvimento.

Entregáveis:

- `paper/EXTERNAL_VALIDATION_ADDENDUM_v1.md`;
- identificação da origem, domínio e independência do conjunto;
- justificativa do tamanho amostral e unidade experimental;
- critérios de inclusão, exclusão, duplicatas e dados ausentes;
- manifesto imutável com SHA-256 dos arquivos, sem revelar resultados;
- endpoints primários e secundários, denominadores e política de abstenção;
- registro OSF público ou sob embargo;
- identificador e data do registro adicionados ao repositório.

Gate A:

- nenhum integrante que execute a análise primária pode abrir resultados ou
  ajustar limiares antes de o adendo estar registrado;
- origem e agrupamento por célula, estudo, lote ou laboratório devem estar
  explícitos;
- alterações posteriores devem entrar no log de desvios, nunca ser chamadas de
  pré-especificadas.

### Frente B — referência humana cega (P0)

**Objetivo:** medir concordância e limites interpretativos sem circularidade.

Entregáveis:

- dois especialistas independentes, idealmente de instituições distintas;
- formulário e manual de anotação versionados;
- pacote cego sem saídas KAIRIS, nomes reveladores ou metadados desnecessários;
- treinamento dos avaliadores apenas com exemplos fora do teste;
- congelamento das anotações antes de mostrar resultados do pipeline;
- adjudicação documentada apenas após as análises independentes;
- concordância interavaliadores e incerteza reportadas.

Gate B:

- pelo menos dois conjuntos completos de anotações independentes;
- abstenção e “indeterminado” preservados como categorias reais;
- a adjudicação não substitui o relatório da discordância original.

### Frente C — baselines, ablações e sensibilidade (P0)

**Objetivo:** mostrar onde o KAIRIS acrescenta informação, onde é equivalente e
onde deve se abster.

Comparações mínimas:

1. Lin-KK do KAIRIS versus uma implementação estabelecida;
2. DRT do KAIRIS versus um solver independente;
3. pipeline completo versus remoção de GSF;
4. pipeline completo versus remoção de ESC;
5. regras determinísticas versus Ollama, mantendo as regras como análise primária;
6. regularização da DRT em grade pré-definida;
7. ruído, truncamento da faixa, redução da densidade de pontos e outliers;
8. análise estratificada de arcos incompletos, componentes indutivos e processos
   sobrepostos.

Para GSF e ESC, que são métodos originais, a validação deve combinar equivalência
de implementação, invariantes matemáticos, referências sintéticas com verdade
conhecida, sensibilidade e associação externa. Não se deve inventar um comparador
“padrão-ouro” que não exista nem afirmar superioridade sem teste apropriado.

Gate C:

- scripts e configurações versionados;
- conjunto de parâmetros definido antes da execução confirmatória;
- todas as variantes reportadas, sem selecionar retrospectivamente a mais
  favorável;
- tempo e memória medidos junto com o desempenho científico.

### Frente D — estatística e análise das discordâncias (P0)

**Objetivo:** transformar resultados em estimativas auditáveis, sem tratar toda
discordância entre observáveis como erro.

Métricas mínimas:

- taxa de importação e de conclusão;
- erro relativo de R∞ e referências Z₀ quando houver verdade apropriada;
- recuperação do número de processos sintéticos;
- erro de localização em `log10(tau)` e área integrada da DRT;
- balanced accuracy, macro-F1, sensibilidade, especificidade e valores
  preditivos quando houver classe de referência;
- matriz de confusão, taxa de abstenção e taxa de inconclusivos;
- IC de 95% por bootstrap agrupado com 2.000 reamostragens e semente congelada;
- tempo de execução, pico de memória e tamanho dos artefatos.

As discordâncias DRT–GSF devem ser estratificadas por família, cobertura de
frequência, ruído, sobreposição de constantes de tempo, indutância,
não-estacionariedade e tipo de referência. O diagnóstico
`intercalation_pseudocapacitive` permanece uma hipótese interpretativa explícita,
não uma prova causal automática.

Gate D:

- divisão por célula/estudo/laboratório, nunca por ponto de frequência;
- intervalos e denominadores presentes em todas as tabelas principais;
- resultados negativos, falhas e abstenções mantidos;
- análise primária executada com LLM desativada.

### Frente E — reprodução e portabilidade (P0)

**Objetivo:** permitir que uma pessoa sem o ambiente de desenvolvimento reproduza
os resultados a partir de uma tag.

Matriz mínima:

| Ambiente | Instalação | Execução obrigatória |
|---|---|---|
| Windows 11 | instalador PowerShell e pacote Python | testes + amostra + corpus de reprodução |
| Ubuntu LTS | shell e Docker | testes + amostra + corpus de reprodução |
| macOS atual, Intel ou Apple Silicon | shell e pacote Python | testes + amostra + corpus de reprodução |
| máquina de 4 GB | sem LLM | amostra e benchmark de memória |
| máquina de 8 GB | sem LLM e Ollama opcional | amostra e benchmark de memória |

Entregáveis:

- comando único para regenerar tabelas e figuras do artigo;
- ambiente travado e imagem Docker sem root;
- workflow de CI para testes e para validação leve;
- relatório de reprodução assinado com sistema, commit, hashes e comandos;
- instruções limpas testadas por uma pessoa que não desenvolveu o pipeline.

Gate E:

- instalação limpa e execução sem intervenção manual não documentada;
- resultados dentro das tolerâncias congeladas nos três sistemas;
- nenhuma dependência obrigatória de Ollama ou de acesso à internet para a análise
  científica, exceto aquisição inicial explicitamente documentada.

### Frente F — dados, licença e proveniência (P0/P1)

**Objetivo:** assegurar que cada entrada e cada saída possam ser citadas,
redistribuídas ou obtidas legalmente.

Entregáveis:

- `data/DATASET_MANIFEST.*` com origem, DOI/URL, licença e papel experimental;
- separação inequívoca entre desenvolvimento, retrospectivo e confirmatório;
- hashes dos arquivos brutos e derivados;
- justificativa para qualquer dado que não possa ser redistribuído;
- script de aquisição quando a redistribuição direta for proibida;
- dicionário de dados e política de anonimização, se aplicável.

Gate F:

- nenhuma amostra sem proveniência e licença verificável entra no pacote público;
- dados restritos não são enviados ao GitHub nem ao artefato público;
- versões derivadas preservam vínculo com o material de origem.

### Frente G — manuscrito, suplemento e comunicação (P0)

**Objetivo:** produzir uma narrativa proporcional à evidência.

Estrutura recomendada do artigo:

1. problema e lacuna;
2. protocolo KAIRIS e observáveis complementares;
3. hipóteses e plano congelado;
4. conjuntos sintéticos, retrospectivos e externos;
5. Lin-KK, DRT, GSF e ESC, com limites de interpretação;
6. baselines, ablações e análise estatística;
7. resultados de engenharia e resultados científicos separados;
8. discordâncias, abstenção e domínio de validade;
9. reprodutibilidade, limitações e trabalho futuro.

O suplemento deve conter parâmetros completos, fluxograma, tabelas expandidas,
resultados de sensibilidade, taxonomia de falhas, formulário humano e informações
necessárias para repetir as análises.

Gate G:

- cada alegação importante aponta para uma tabela, figura ou teste;
- mecanismo causal não é inferido apenas de DRT, GSF ou ESC;
- os 198 espectros são descritos como retrospectivos;
- uso de IA na programação ou redação é declarado conforme a política do
  periódico escolhido;
- todos os autores aprovam a versão submetida e suas contribuições CRediT.

### Frente H — preparação JOSS (P1)

**Objetivo:** deixar o software editorialmente pronto sem confundir essa meta com
a data de elegibilidade.

Até 16 de fevereiro:

- `paper.md` e `paper.bib` no formato JOSS;
- `CITATION.cff`, licença OSI, guia de contribuição e código de conduta;
- documentação de instalação, uso, testes, API e exemplos;
- release arquivada com DOI;
- demonstração de uso em pesquisa e, idealmente, teste por usuário externo;
- issues e pull requests públicos usados para o desenvolvimento real;
- declaração de uso de IA, quando aplicável.

O repositório foi tornado público em 2 de novembro de 2026. A regra atual do JOSS
exige mais de seis meses de histórico público com atividade distribuída; por isso,
a primeira data conservadora de submissão é 3 de maio de 2027. Não se deve criar
commits artificiais: o histórico deve refletir desenvolvimento, releases, issues,
revisões e contribuição reais.

## 5. Cronograma operacional

### Fase 0 — decisões e bloqueios (4–10 de novembro de 2026)

**Prioridade absoluta:** definir aquilo que depende de pessoas e dados externos.

- escolher o periódico científico-alvo e um periódico alternativo;
- fechar autores provisórios, afiliações, ORCID e autor correspondente;
- confirmar domínio e fonte do conjunto externo;
- obter aceite de dois especialistas e datas de entrega;
- escolher administrador(es) do registro OSF;
- decidir registro público ou embargo e política de acesso cego;
- redigir a primeira versão do adendo externo;
- abrir issues públicas para cada frente do roadmap.

**Marco M0 — 10/11:** fonte externa, avaliadores e periódico definidos.

**No-go:** sem fonte externa confirmada até esta data, reduzir o escopo do artigo
ou renegociar a data de submissão; não substituir silenciosamente por dados já
vistos.

### Fase 1 — congelamento prospectivo (11–17 de novembro)

- concluir tamanho amostral e unidade experimental;
- fechar endpoints, exclusões, subgrupos e análise de ausências;
- definir o que os analistas podem ver durante o cegamento;
- gerar manifesto e hashes sem inspecionar os resultados;
- revisar o adendo por uma segunda pessoa;
- registrar o protocolo no OSF e registrar identificador/data no GitHub;
- criar uma tag imutável do adendo.

**Marco M1 — 17/11:** estudo externo registrado antes da abertura dos resultados.

### Fase 2 — instrumentação de validação (18 de novembro–1 de dezembro)

- implementar executores de baselines, ablações e sensibilidade;
- criar validação automática das tabelas finais;
- definir formatos das anotações humanas e validá-los por schema;
- preparar pacote cego e exemplos de treinamento fora do teste;
- implementar medição reprodutível de tempo e memória;
- executar apenas dados de desenvolvimento para depuração;
- congelar scripts e parâmetros da análise confirmatória.

**Marco M2 — 01/12:** análise confirmatória executável sem decisões manuais.

### Fase 3 — coleta cega e execução (2–20 de dezembro)

- entregar o pacote cego aos especialistas;
- executar KAIRIS sem LLM no conjunto externo;
- executar baselines sem alterar parâmetros após ver resultados;
- preservar logs, hashes, configuração e ambiente;
- não compartilhar resultados entre avaliadores;
- registrar incidentes técnicos e desvios no momento em que ocorrerem.

**Marco M3 — 20/12:** resultados computacionais congelados e revisão humana em
andamento.

### Fase 4 — conclusão humana e janela de contingência (21 de dezembro–5 de janeiro)

- receber e validar completude das anotações;
- solicitar apenas correções formais, sem induzir mudança de interpretação;
- congelar os dois conjuntos de anotações;
- usar a janela de fim de ano para falhas de coleta, nunca para otimizar limiares;
- preparar scripts de desbloqueio e análise estatística.

**Marco M4 — 05/01:** duas avaliações independentes congeladas.

**No-go:** se um avaliador não concluir, ativar o especialista reserva; não reduzir
para um único avaliador sem declarar desvio maior.

### Fase 5 — desbloqueio e análise (6–19 de janeiro de 2027)

- desbloquear comparações após todos os congelamentos;
- executar análise estatística primária uma única vez;
- calcular concordância interavaliadores antes da adjudicação;
- adjudicar casos definidos pelo protocolo;
- classificar discordâncias DRT–GSF e falhas por taxonomia;
- gerar tabelas e figuras por scripts, sem edição manual dos valores;
- distinguir análises confirmatórias das exploratórias;
- atualizar o log de desvios.

**Marco M5 — 19/01:** resultados principais e suplemento numérico completos.

### Fase 6 — redação e release candidate (20–31 de janeiro)

- completar Métodos e Resultados a partir dos artefatos congelados;
- finalizar Introdução, Discussão e limitações;
- gerar figuras e tabelas finais de forma automatizada;
- completar manifesto de dados, checklist de reprodutibilidade e materiais JOSS;
- criar `v1.0.0-rc1` em commit limpo;
- iniciar reprodução independente a partir de um clone novo.

**Marco M6 — 31/01:** manuscrito completo, não apenas estrutura ou rascunho parcial.

### Fase 7 — reprodução e revisão interna (1–7 de fevereiro)

- reproduzir em Windows, Ubuntu e macOS;
- testar pelo menos um ambiente de 4 GB e um de 8 GB;
- verificar todos os links, DOIs, licenças, hashes e comandos;
- revisão científica por alguém que não escreveu a seção avaliada;
- revisão estatística e de linguagem;
- resolver somente defeitos que afetem correção ou reprodução.

**Marco M7 — 07/02:** reprodução independente aprovada ou desvios explicitados.

### Fase 8 — congelamento editorial (8–12 de fevereiro)

- incorporar revisões finais;
- executar testes, gates e geração do artigo pela última vez;
- conferir correspondência entre texto, tabelas, figuras e suplemento;
- congelar código e dados como `v1.0.0`;
- arquivar a release em repositório com DOI;
- registrar versões exatas no manuscrito;
- obter aprovação formal de todos os autores.

**Marco M8 — 12/02:** pacote final aprovado, com quatro dias de margem.

### Fase 9 — submissão (13–16 de fevereiro)

- preencher metadados e declarações do periódico;
- anexar manuscrito, suplemento, checklists, registro e links arquivados;
- conferir arquivos renderizados no sistema editorial;
- submeter até 16 de fevereiro e arquivar o comprovante;
- abrir issue pós-submissão para respostas editoriais, sem alterar a release citada.

**Marco M9 — 16/02:** artigo científico submetido.

**Marco posterior — ≥03/05:** verificar novamente os critérios vigentes e, se
atendidos, submeter o artigo de software ao JOSS.

## 6. Matriz de evidência e alegações

| Alegação | Evidência exigida | Estado inicial |
|---|---|---|
| O pipeline importa e conclui o corpus declarado | testes, logs e artefatos | disponível retrospectivamente |
| GSF e ESC independentes equivalem aos módulos integrados | gates H3 e H5 | disponível |
| Invariantes matemáticos de GSF/ESC são preservados | gates H4 e H6 | disponível |
| Parâmetros simples são recuperados com erro limitado | sintéticos com verdade conhecida | parcial |
| O desempenho generaliza para dados não usados no desenvolvimento | conjunto externo pré-registrado | pendente |
| As classificações têm relação mensurável com avaliação especializada | revisão cega por dois especialistas | pendente |
| Cada módulo adiciona informação útil | ablações e análise de discordâncias | pendente |
| O resultado é reproduzível nos três sistemas | reprodução independente | parcial |
| A LLM melhora explicações sem alterar a análise primária | comparação secundária | opcional |

## 7. Política de versões e congelamentos

- `validation-plan-v1.0`: permanece imutável;
- nova versão do adendo externo: criada antes do acesso confirmatório;
- tag de análise: criada depois do pré-registro e antes da execução;
- `v1.0.0-rc1`: primeira reprodução integral do artigo;
- `v1.0.0`: código, configuração e materiais citados na submissão;
- correções posteriores: `v1.0.1`, sem reescrever a tag citada;
- toda mudança em endpoint, exclusão ou limiar entra em
  `paper/DEVIATIONS_LOG_v1.md` com data, motivo, momento e impacto.

## 8. Responsabilidades mínimas

Uma pessoa pode acumular funções, mas as decisões devem permanecer identificáveis.

| Função | Responsabilidade |
|---|---|
| responsável científico | escopo, hipóteses, decisões de no-go e aprovação final |
| responsável de dados | licenças, manifesto, hashes, cegamento e acesso |
| responsável de software | executores, testes, releases e correções rastreáveis |
| responsável estatístico | plano, scripts, denominadores, ICs e auditoria |
| especialistas 1 e 2 | avaliação independente e declaração de conflitos |
| reprodutor independente | instalação limpa e relatório de reprodução |
| autores | contribuições CRediT, revisão e aprovação da submissão |

O responsável científico não deve adjudicar silenciosamente erros de dados ou
alterar rótulos depois de conhecer a previsão do KAIRIS.

## 9. Registro de riscos

| Risco | Sinal antecipado | Mitigação | Limite de decisão |
|---|---|---|---|
| dados externos atrasados | sem acordo em 10/11 | fonte reserva e escopo mínimo pré-definido | 10/11 |
| avaliador atrasa | sem aceite ou cronograma | especialista reserva e formulário curto | 05/01 |
| licença impede publicação | termos ausentes | manifesto, permissão ou script de aquisição | antes do OSF |
| vazamento confirmatório | resultados abertos cedo | separar acesso, hashes e registro temporal | invalida caráter prospectivo |
| baseline difícil de instalar | falha no conjunto de desenvolvimento | container/versão fixada e relatório de limitação | 01/12 |
| baixa concordância humana | categorias ambíguas | reportar incerteza; não apagar discordância | não mudar rótulos pós-hoc |
| falha de portabilidade | diferença acima da tolerância | issue bloqueadora e reexecução integral | 07/02 |
| escopo cresce | novas features após M2 | mover para backlog pós-submissão | revisão semanal |
| resultado negativo | gate científico falha | publicar resultado e limitar alegação | nunca ajustar limiar retroativamente |
| JOSS inelegível em fevereiro | histórico público <6 meses | pacote pronto; submissão em maio | regra editorial vigente |

## 10. Cadência de governança

- reunião curta semanal com estado de M0–M9;
- quadro público com colunas `backlog`, `ready`, `in progress`, `review` e `done`;
- uma issue por entregável, sempre ligada a um marco;
- pull request obrigatório para mudanças científicas ou de análise;
- revisão por segunda pessoa para scripts que gerem resultados do artigo;
- relatório semanal contendo: progresso, bloqueios, desvios e risco à data final;
- nenhuma tarefa é “concluída” apenas porque o código roda: deve haver artefato,
  teste, revisão e vínculo com o endpoint correspondente.

## 11. Critérios globais de pronto para submissão

Em 12 de fevereiro, todos os itens abaixo devem estar verdadeiros:

- [ ] adendo externo registrado antes da abertura dos resultados;
- [ ] manifesto de dados, licenças e hashes completo;
- [ ] análise primária sem LLM executada a partir de tag limpa;
- [ ] duas avaliações humanas independentes congeladas;
- [ ] baselines, ablações e sensibilidades executados como planejado;
- [ ] métricas com ICs, denominadores, agrupamento e abstenções;
- [ ] falhas, resultados negativos e desvios preservados;
- [ ] artigo e suplemento completos e coerentes com os artefatos;
- [ ] reprodução independente em Windows, Linux e macOS;
- [ ] execução documentada em 4 GB e 8 GB;
- [ ] release `v1.0.0` e arquivo com DOI disponíveis;
- [ ] autores, ORCID, CRediT, conflitos, financiamento e uso de IA declarados;
- [ ] todos os autores aprovaram a versão final;
- [ ] pacote JOSS pronto, ainda que aguardando elegibilidade temporal.

## 12. Backlog após a submissão

Salvo se indispensáveis para corrigir uma falha P0, ficam para depois de 16 de
fevereiro:

- fine-tuning ou treinamento automático de LLM;
- expansão do painel sem impacto na reprodução;
- novos diagnósticos não pré-especificados;
- novos eletrólitos sem relação com o conjunto do artigo;
- otimizações de desempenho não necessárias para 4 GB/8 GB;
- ampliação exploratória do corpus;
- APIs e integrações externas adicionais;
- novos módulos além de Lin-KK, DRT, GSF e ESC.

Essas atividades podem continuar como desenvolvimento público real no caminho
para a submissão ao JOSS em maio de 2027.

## 13. Próxima ação imediata

O próximo artefato prioritário é
`paper/EXTERNAL_VALIDATION_ADDENDUM_v1.md`. Ele deve ser preenchido e revisado até
17 de novembro, registrado no OSF antes da abertura dos resultados e ligado a uma
tag Git. Em paralelo, devem ser confirmados os dois especialistas e a fonte do
conjunto externo. Nenhuma nova funcionalidade supera essas três tarefas em
prioridade científica.

## Referências operacionais

- [Requisitos de submissão do JOSS](https://joss.readthedocs.io/en/latest/submitting.html)
- [Critérios de revisão do JOSS](https://joss.readthedocs.io/en/latest/review_criteria.html)
- [Registros e pré-registros no OSF](https://help.osf.io/article/330-welcome-to-registrations)
