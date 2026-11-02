# Protocolo KAIRIS de revisão especializada cega — versão 1

**Estado:** protocolo retrospectivo; requer aprovação do pesquisador responsável  
**Unidade avaliada:** um espectro EIS completo  
**Revisores:** no mínimo dois especialistas, trabalhando independentemente

## Objetivo

Estimar a concordância humana e comparar, sem vazamento de informação, a leitura
especializada dos espectros com os regimes e alertas produzidos por DRT e GSF.
Esta etapa cobre sobretudo respostas distribuídas, difusivas, indutivas ou
degradadas, para as quais não existe uma verdade única de picos DRT.

## Cegamento

O script `scripts/build_blinded_review_pack.py` substitui nomes por identificadores
aleatórios, randomiza a ordem e entrega apenas dados EIS brutos e gráficos Nyquist
e Bode. Origem, família sintética, diagnósticos KAIRIS e chave de correspondência
ficam em `coordinator_only`, inacessível aos revisores até o congelamento das
anotações.

Cada revisor recebe uma cópia independente do formulário. Discussão entre
revisores e consulta ao relatório KAIRIS são proibidas antes da primeira rodada.

## Variáveis anotadas

1. qualidade do espectro: aceitável, questionável ou inutilizável;
2. resposta dominante: cinética, difusiva, pseudocapacitiva, mista, indutiva ou
   indeterminada;
3. número aparente de processos: 0 a 5 ou indeterminado;
4. compatibilidade com pseudocapacitância de intercalação: sim, não ou incerta;
5. confiança de 1 a 5;
6. exclusão proposta, sempre acompanhada de justificativa textual.

## Procedimento

1. O coordenador gera e arquiva o pacote e seu `pack_manifest.json`.
2. Dois revisores anotam todos os casos selecionados de modo independente.
3. Os CSVs preenchidos são tornados somente leitura e recebem SHA-256.
4. Calcula-se concordância antes de qualquer adjudicação.
5. Divergências são discutidas por ambos; se persistirem, um terceiro especialista
   adjudica sem receber o resultado do KAIRIS.
6. A chave é aberta somente depois do congelamento das decisões humanas.

## Análise estatística pré-especificada

- kappa de Cohen para qualidade, resposta dominante e indicação de
  pseudocapacitância de intercalação;
- kappa ponderado para número de processos e confiança;
- concordância bruta e matriz de confusão, sempre com IC de 95%;
- sensibilidade, especificidade, valor preditivo e taxa de abstenção do KAIRIS
  somente quando a decisão humana adjudicada definir uma referência adequada;
- resultados separados por origem e por família, sem tratar espectros da mesma
  célula ou campanha como observações independentes.

Após receber os dois formulários congelados, a análise reprodutível é executada
sem abrir a chave de identificação:

```bash
python scripts/analyze_blinded_reviews.py reviewer_a.csv reviewer_b.csv \
  --destination output/review_agreement_v1
```

O script produz kappa de Cohen, kappa quadrático ponderado, concordância bruta,
IC de 95% por bootstrap, taxas de abstenção e uma lista separada de divergências
para adjudicação.

Ausências e respostas `indeterminada` não serão convertidas em erros. Serão
relatadas como abstenções e analisadas separadamente.

## Limitações e uso no artigo

O corpus atual já foi inspecionado durante o desenvolvimento; portanto, esta
revisão é retrospectiva. O mesmo procedimento deverá ser registrado antes da
abertura de um conjunto externo para sustentar alegações confirmatórias.

