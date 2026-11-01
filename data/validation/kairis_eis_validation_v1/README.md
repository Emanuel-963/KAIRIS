# KAIRIS EIS Validation Corpus v1

Este corpus testa importação, Lin-KK, DRT, GSF, ESC e geração do relatório do
KAIRIS. Ele separa explicitamente dados sintéticos com verdade de gerador de
dados experimentais públicos sem rótulo científico inventado.

## Conteúdo

- `synthetic/`: 72 espectros determinísticos, organizados em 12 famílias e seis
  variantes por família;
- `public/zenodo_15422339_nmc811_30soc/`: 54 espectros experimentais de células
  NMC811 21700 a 30% de SoC, preservados byte a byte da fonte;
- `public/autoecm_ccby4/`: conjuntos de treino e teste publicados pelo AutoECM,
  com 45 exemplos de treino e 27 de holdout convertidos nas nove classes;
- `dataset_manifest.csv`: catálogo único com origem, papel recomendado, faixa de
  frequência, família, licença e SHA-256;
- `synthetic_truth.csv`: parâmetros do gerador e desafio esperado de cada caso;
- `public_manifest.csv`: proveniência dos arquivos experimentais;
- `validation_evidence/`: auditoria de integridade e, quando executado, resultado
  dos cinco agentes;
- `TRAINING_AND_SPLITS.md`: política para treinamento sem vazamento de dados;
- `ATTRIBUTION.md`: DOI, autores e licença dos dados públicos.

O corpus diretamente executável contém 198 espectros: 72 sintéticos KAIRIS, 72
sintéticos rotulados da publicação AutoECM e 54 experimentais. Os sintéticos
cobrem Randles/RC, ZARC/CPE, duas e três relaxações, Warburg semi-infinito,
difusão finita transmissiva/refletiva, Gerischer, resposta porosa distribuída,
laço indutivo de adsorção, indutância de cabos, deriva não estacionária e
aquisição esparsa com outliers. Há arquivos CSV/TXT com separador vírgula,
ponto-e-vírgula ou tabulação, decimal ponto ou vírgula, cabeçalho direto ou
preâmbulo semelhante ao EC-Lab.

## Reproduzir e auditar

Na raiz do projeto:

```powershell
python scripts/build_validation_dataset.py
python scripts/validate_eis_corpus.py
```

No Linux, os comandos são idênticos com `python3`. O primeiro comando só recria
os sintéticos. Dados públicos só são baixados mediante opção explícita:

```powershell
python scripts/build_validation_dataset.py --download-public
```

Para executar os cinco agentes sem LLM em todos os 198 espectros:

```powershell
python scripts/validate_eis_corpus.py --full-pipeline
```

Um teste curto pode usar `--limit 3`. Relatórios completos ficam em
`output/validation_corpus/reports/`. A evidência compacta fica em
`validation_evidence/pipeline_results.csv` e registra separadamente conclusão do
pipeline e concordância DRT–GSF. Divergência científica não é tratada como falha
de engenharia: o Agente 5 ainda deve produzir um relatório que explicite a
divergência.

## Base científica e limites

As funções sintéticas implementam elementos usuais de espectroscopia de
impedância; não reproduzem curvas digitalizadas de artigos. A formulação e o uso
de RC/CPE, Warburg, difusão finita, Gerischer e linhas de transmissão porosas são
baseados na taxonomia clássica de *Electrochemical Impedance Spectroscopy and its
Applications* (Lasia, DOI `10.1007/978-1-4614-8933-7`) e no modelo de eletrodo
poroso de de Levie (DOI `10.1016/0013-4686(63)80042-0`). Ruído, deriva e outliers
são desafios controlados, não medições reais.

O conjunto público é um *holdout* experimental externo. Ele não contém a verdade
de um circuito equivalente, DRT ou interpretação causal. O fato de o KAIRIS
terminar a análise não torna uma interpretação automaticamente correta.

