# Uso para treinamento e validação

## Papéis recomendados

- **Sintéticos:** desenvolvimento, teste de importação, testes de regressão e
  pré-treinamento de classificadores de morfologia. Os parâmetros do gerador são
  rótulos de processo conhecidos, mas não provam identificabilidade de um único
  circuito a partir da curva.
- **54 células públicas:** avaliação externa agrupada por origem. Por serem
  células do mesmo lote e condição, não se deve espalhar aleatoriamente espectros
  correlacionados entre treino e teste.
- **AutoECM publicado:** benchmark de classificação com rótulos de circuito,
  útil para treino numérico. Separe por classe e preserve um conjunto de teste
  que não tenha sido usado para escolher hiperparâmetros.
- **Interpretação da LLM:** só entra no `output/training/dataset.jsonl` depois de
  aprovação ou correção humana no painel KAIRIS. Saídas automáticas destes
  espectros não são rótulos científicos.

## Divisão sem vazamento

Para experimentos numéricos, faça a separação por família sintética e por fonte
experimental, nunca por pontos individuais de frequência. Uma política segura é:

1. treino/desenvolvimento com parte das variantes sintéticas;
2. validação com variantes sintéticas inteiras não vistas;
3. teste final com famílias mantidas fora do treino;
4. avaliação externa separada nas 54 células Zenodo.

Se dados adicionais de uma publicação forem incorporados, todos os espectros do
mesmo artigo, célula, campanha ou lote devem permanecer no mesmo grupo. Registre
DOI, licença, transformação e hash antes do uso.

## Relação com o aprendizado supervisionado do KAIRIS

Este corpus fornece entradas e verdades físicas do gerador; ele não substitui o
dataset de conversação revisado. Execute o pipeline, revise cada conclusão no
painel e somente então use `output/training/dataset.jsonl` para SFT/LoRA. Casos
com Lin-KK reprovado ou divergência DRT–GSF são particularmente úteis para ensinar
respostas cautelosas, desde que a correção seja escrita por um pesquisador.

