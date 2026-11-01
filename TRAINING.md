# Aprendizado supervisionado do KAIRIS

O Ollama é um servidor de inferência e não modifica os pesos do modelo ao receber
novas respostas. O KAIRIS implementa um fluxo supervisionado que produz melhoria
imediata por exemplos revisados e prepara dados reproduzíveis para um fine-tuning
posterior.

## Fluxo implementado

1. O Agente 5 gera a interpretação por regras e, quando habilitada, pela LLM.
2. Um pesquisador abre o painel e aprova, corrige ou rejeita a interpretação.
3. A avaliação é acrescentada atomicamente a `output/training/feedback.json`.
4. O KAIRIS mantém somente a revisão mais recente de cada combinação de amostra e
   SHA-256 no dataset `output/training/dataset.jsonl`.
5. Aprovações usam a resposta original; correções usam exclusivamente o texto
   revisado; rejeições são excluídas do dataset.
6. Até três exemplos validados recentes são incorporados ao próximo prompt, dentro
   do orçamento configurado.

Respostas não revisadas nunca entram no dataset automaticamente.

## Configuração

```json
{
  "supervised_learning_enabled": true,
  "supervised_examples_in_prompt": 3,
  "supervised_examples_max_chars": 5000,
  "finetune_min_validated_examples": 50
}
```

O limite de 50 exemplos apenas sinaliza que existe massa crítica inicial para
avaliar um experimento. Ele não garante qualidade suficiente. Diversidade de
eletrólitos, instrumentos, morfologias e regimes é mais importante que quantidade
bruta.

## Estrutura do dataset

Cada linha JSONL contém mensagens `system`, `user` e `assistant`, além de metadados
com amostra, hash da entrada, veredito e ID da revisão. O formato é adequado para
conversão posterior a ferramentas de SFT/LoRA.

## Fine-tuning de pesos

O treinamento de pesos deve ocorrer em ambiente separado, preferencialmente com GPU,
e somente depois de:

- revisão científica do dataset exportado;
- separação por experimento em treino, validação e teste, evitando vazamento entre
  espectros correlacionados;
- escolha explícita do modelo-base e de sua licença;
- definição de métricas de fidelidade factual e não apenas similaridade textual;
- comparação contra o modelo original e contra as regras determinísticas.

Após validação, um adaptador LoRA pode ser combinado ou distribuído com o modelo e
convertido para um formato aceito pelo Ollama. A atualização automática do projeto
pode então distribuir a nova configuração de modelo. Modelos ou dados de pesquisa
não são enviados automaticamente para nenhum servidor pelo KAIRIS.
