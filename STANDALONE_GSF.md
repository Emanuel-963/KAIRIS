# GSF independente

Este ramo disponibiliza o **Golden Spectral Field (GSF)** como análise autônoma.
O GSF é um método analítico original criado pelo autor do KAIRIS e permanece um
dos módulos científicos do protocolo integrado **KAIRIS — Kramers–Kronig-Assessed
Impedance, Relaxation, and Integrated Spectroscopy**.

Este comando não executa DRT, ESC nem o orquestrador. Ele lê diretamente um
espectro EIS, normaliza o plano complexo e calcula mapa q, α, kφ, gradiente S,
índice crítico e regime GSF. Os resultados incluem JSON e três figuras SVG.

## Uso

```bash
python -m pip install -e .
kairis-gsf caminho/espectro.csv --output resultados_gsf
```

Um diretório também pode ser processado recursivamente:

```bash
kairis-gsf caminho/dataset --output resultados_gsf
```

Use `--overwrite` para substituir resultados existentes. A independência do
módulo não altera sua integração ou sua atribuição no artigo científico KAIRIS.

## Atribuição científica

O histórico Git registra a disponibilização deste ramo e a relação com o KAIRIS.
A referência bibliográfica definitiva deve apontar para o artigo do método quando
ele estiver publicado. Nome científico completo e ORCID do autor serão incluídos
nos metadados de citação antes da release acadêmica.
