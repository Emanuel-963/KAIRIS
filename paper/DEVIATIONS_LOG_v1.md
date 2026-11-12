# Registro de desvios do plano de validação KAIRIS v1.0

**Plano de referência:** `paper/VALIDATION_PLAN_v1.md`  
**Início do registro:** 3 de novembro de 2026  

Nenhum desvio registrado no momento do congelamento.

## 4 de novembro de 2026 — emenda terminológica sem alteração de endpoints

- **Responsável:** pesquisador responsável.
- **Etapa afetada:** nomenclatura pública de ESC e formulação da alegação de
  novidade no plano v1.0.
- **Descrição:** a denominação anterior da ESC foi substituída por
  “Electrochemical Spectral Cartography”. O plano passou a declarar explicitamente que a
  transformação bilinear impedância--coeficiente de reflexão é a transformação
  clássica de Smith e não é uma contribuição original do KAIRIS.
- **Motivo e momento:** busca de anterioridade realizada antes da análise do
  conjunto confirmatório externo e antes de qualquer submissão.
- **Impacto esperado:** nenhum; fórmulas, endpoints, limiares, corpus e gates
  H1--H6 permanecem inalterados.
- **Ação corretiva:** nomenclatura atualizada no código, relatórios, manuscrito e
  documentação; estratégia de novidade documentada em relatórios próprios.
- **Classificação:** emenda pré-dados confirmatórios, sem mudança analítica.

Em 4 de novembro de 2026, os documentos públicos da avaliação humana também
foram desidentificados por decisão expressa do pesquisador. Identidades,
qualificações e relações acadêmicas passaram a ser mantidas somente nos
registros privados do coordenador. Essa mudança não altera papéis, regras de
ativação, cegamento ou endpoints.

Todo registro futuro deverá informar:

1. data e responsável;
2. etapa afetada e commit;
3. descrição do desvio;
4. motivo e momento em relação à abertura dos resultados;
5. impacto esperado nos endpoints;
6. ação corretiva e análises repetidas;
7. classificação como correção de bug, emenda pré-dados ou desvio pós-dados.

Entradas não serão apagadas. Correções serão acrescentadas como novas entradas.

## 12 de novembro de 2026 — correção do denominador de P2

- **Responsável pela implementação:** Codex, a pedido do pesquisador.
- **Etapa afetada:** análise confirmatória P2 em
  `scripts/analyze_external_confirmation.py`. Referência original:
  `94a03c366b0d26ec8f2e05befed0660fb2ff0f1d`.
- **Descrição:** o analisador registrava os casos elegíveis com JSON ausente
  e depois os excluía da matriz, das métricas e do bootstrap. Agora esses
  casos recebem a resposta de avaliação `undetermined` e conservam o
  registro separado de saída ausente.
- **Momento e impacto:** correção pré-análise, verificada com dados simulados.
  Aplica o denominador definido no plano congelado e afeta P2 quando falta
  uma saída em caso com consenso elegível. A identidade da versão corrigida
  será registrada no commit que incorporar esta correção e no pacote OSF
  regenerado antes do registro.
- **Classificação:** correção de implementação do endpoint congelado.
