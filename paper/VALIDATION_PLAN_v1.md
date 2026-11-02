# Plano de validação científica do KAIRIS — versão 1

**Estado:** rascunho para aprovação do pesquisador responsável  
**Data de congelamento técnico:** 1 de novembro de 2026  
**Versão do protocolo:** anterior à release candidata v1.0  

## 1. Declaração de transparência

Os 198 espectros do corpus atual e parte de seus resultados já foram examinados
durante o desenvolvimento. Portanto, eles serão tratados como validação
retrospectiva, desenvolvimento e teste de robustez. Não serão descritos no artigo
como conjunto confirmatório intocado.

Uma validação confirmatória exigirá um conjunto externo futuro cuja coleta,
seleção, exclusões, métricas e limiares sejam registrados antes da abertura dos
resultados.

## 2. Pergunta científica principal

O KAIRIS produz, de forma reproduzível e auditável, descritores complementares de
espectros EIS por Lin-KK, DRT, GSF e ESC, preservando a capacidade de sinalizar
divergência ou insuficiência de evidência sem depender de uma LLM?

## 3. Alegações permitidas nesta fase

O estudo poderá avaliar se o KAIRIS:

1. importa formatos heterogêneos de EIS;
2. executa os cinco agentes sem falhas de infraestrutura;
3. recupera referências simples conhecidas em espectros sintéticos ideais;
4. produz resultados idênticos ou numericamente equivalentes em ambientes
   declarados;
5. identifica e relata desacordos entre DRT e GSF;
6. gera relatórios e proveniência completos sem LLM.

Não será alegado, sem evidência adicional, que:

- existe um único circuito equivalente identificável para cada espectro;
- toda divergência entre agentes representa erro;
- DRT, GSF ou ESC identificam causalmente um mecanismo eletroquímico;
- a interpretação da LLM substitui avaliação especializada;
- os 198 espectros constituem validação externa independente de todos os módulos.

## 4. Papéis dos conjuntos atuais

| Conjunto | Papel no estudo |
|---|---|
| 72 sintéticos KAIRIS | desenvolvimento, regressão e caracterização de falhas |
| AutoECM 45 treino | desenvolvimento de classificadores e comparações exploratórias |
| AutoECM 27 teste | benchmark retrospectivo; não é mais holdout intocado |
| Zenodo NMC811, 54 células | avaliação externa retrospectiva de um único domínio |
| Dados futuros independentes | validação confirmatória prospectiva |

Espectros correlacionados da mesma célula, campanha, artigo ou lote permanecerão no
mesmo grupo. Pontos de frequência nunca serão divididos entre treino e teste.

## 5. Endpoints primários de desenvolvimento

Os critérios executáveis estão em `config/validation_acceptance_v1.json`.

### 5.1 Integridade e proveniência

- 100% das amostras devem possuir JSON consolidado e relatório HTML.
- 100% dos hashes de entrada devem coincidir com o manifesto.
- 100% dos artefatos da release devem registrar árvore Git limpa.
- 100% dos artefatos devem registrar o commit atual da release.
- Nenhum resultado pode ser reutilizado na execução de release.

### 5.2 Referência sintética ideal de Randles

Para os seis espectros `randles_rc`:

- aprovação Lin-KK em pelo menos 95%;
- exatamente um pico DRT em pelo menos 95%;
- erro relativo mediano de R∞ no máximo 2%;
- pior erro relativo de R∞ no máximo 5%;
- erro mediano de localização do pico no máximo 0,10 década em log10(τ);
- pior erro de localização do pico no máximo 0,20 década em log10(τ).

Esses limiares são critérios de desenvolvimento escolhidos após contato com o
corpus atual. Eles não são endpoints confirmatórios prospectivos.

### 5.3 Recuperação sintética multirrelaxação

O script `scripts/analyze_synthetic_recovery.py` faz correspondência um a um por
erro mínimo em log10(τ) nas famílias com tempos característicos definidos
analiticamente: Randles, ZARC simples, ZARC duplo e ZARC triplo. Serão relatados
número de picos, fração de processos pareados, erro de τ e erro de R∞, com IC de
95% por bootstrap para medianas.

Famílias difusivas, distribuídas, indutivas, com deriva ou outliers não serão
forçadas a uma verdade de picos DRT. Seus resultados permanecem descritivos e são
encaminhados à revisão humana cega. Como esta análise foi definida após inspeção
do corpus, ela é retrospectiva e não cria novos critérios confirmatórios.

### 5.4 Robustez e domínio operacional

O script `scripts/run_robustness_benchmark.py` executa três experimentos
controlados, com semente e réplicas registradas: separação logarítmica entre duas
relaxações, ruído relativo e truncamento da frequência máxima. Os endpoints são
taxa de recuperação dos processos, erro de localização de τ e erro relativo de
R∞. O objetivo é estabelecer um domínio operacional e critérios de abstinência,
não otimizar parâmetros por amostra.

As curvas e limiares encontrados são específicos dos modelos sintéticos usados.
Qualquer alteração do solver motivada por esses resultados exigirá nova versão do
benchmark e deverá ser congelada antes da abertura das avaliações humanas.

## 6. Endpoints descritivos

Serão relatados sem transformar automaticamente divergência em falha:

- taxa Lin-KK por origem e família;
- número de picos DRT;
- resíduos do ajuste DRT;
- regimes DRT e GSF;
- frequência e tipo de divergência DRT–GSF;
- comportamento dos quatro grupos ESC;
- tempo de execução e memória;
- falhas, abstenções e mensagens de cautela.

## 7. Validação confirmatória futura

Antes de abrir o futuro conjunto externo, deverão ser aprovados:

1. domínio eletroquímico e origem independente;
2. tamanho amostral e unidade independente real;
3. critérios de inclusão e exclusão;
4. tratamento de replicatas e espectros correlacionados;
5. verdades ou avaliações de referência;
6. protocolo de anotação cega por pelo menos dois especialistas;
7. métricas, intervalos de confiança e tratamento de ausências;
8. política de abstinência;
9. análise primária e análises secundárias;
10. local de registro público do plano.

O procedimento operacional de anotação está em
`paper/BLINDED_REVIEW_PROTOCOL_v1.md`. O pacote cego deve ocultar nomes, origem,
família e resultados dos agentes, incluir controles em ordem aleatória e manter a
chave exclusivamente com o coordenador até o congelamento das avaliações.

## 8. LLM

A análise primária será executada com LLM desativada. O modo Ollama será tratado
como análise secundária. Toda avaliação da LLM registrará modelo, quantização,
prompt, temperatura, memória, exemplos supervisionados e intervenção humana.

O dataset de conversação deverá ser dividido por experimento, não por resposta.
Nenhuma amostra do teste confirmatório poderá entrar na memória, nos exemplos de
prompt ou em fine-tuning antes do encerramento da análise.

## 9. Execução reproduzível

A execução candidata deverá partir de commit limpo e diretório de saída vazio:

```powershell
python scripts/run_release_validation.py `
  --output output/validation_release_v1 `
  --require-tag
```

O comando recusa árvore Git modificada e saída preexistente, executa o corpus sem
LLM, grava evidências fora da árvore versionada, avalia os critérios e produz um
manifesto com hashes.

## 10. Aprovações pendentes

Antes de declarar este plano congelado para o artigo, o pesquisador responsável
deve aprovar:

- pergunta principal e alegações permitidas;
- limiares da referência Randles;
- domínios e tamanho do conjunto confirmatório;
- protocolo de anotação por especialistas;
- método estatístico e intervalos de confiança;
- política para resultados inconclusivos;
- periódico-alvo e formato de disponibilização dos dados.
