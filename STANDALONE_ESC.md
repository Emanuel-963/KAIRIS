# ESC independente

Este ramo disponibiliza o **Emanuel–Smith Chart (ESC)** como análise autônoma.
O ESC é um método analítico original criado pelo autor do KAIRIS e permanece um
dos módulos científicos do protocolo integrado **KAIRIS — Kramers–Kronig-Assessed
Impedance, Relaxation, and Integrated Spectroscopy**.

O comando lê EIS bruto e recebe uma ou mais referências Z₀ explicitamente. Ele
não executa DRT, GSF ou o orquestrador e não atribui significado físico automático
às referências. Essa separação impede que uma hipótese de Z₀ seja confundida com
uma medida ou com uma saída de outro método.

## Uso

```bash
python -m pip install -e .
kairis-esc espectro.csv --z0 R_INF=12.4 --output resultados_esc
```

Referências reais e complexas podem ser comparadas no mesmo relatório:

```bash
kairis-esc espectro.csv \
  --z0 R_INF=12.4 \
  --z0 DRT_PEAK=8.1,-0.2 \
  --output resultados_esc
```

O resultado contém JSON auditável e HTML interativo com frequência no tooltip,
zoom e pan. Um diretório de EIS também pode ser processado recursivamente.

## Atribuição científica

O histórico Git registra a disponibilização deste ramo e a relação com o KAIRIS.
A referência bibliográfica definitiva deve apontar para o artigo do método quando
ele estiver publicado. Nome científico completo e ORCID do autor serão incluídos
nos metadados de citação antes da release acadêmica.
