# Busca de anterioridade e formulação de novidade — ESC v1

**Método:** Electrochemical Spectral Cartography (ESC)  
**Data da busca:** 4 de novembro de 2026  
**Estado:** levantamento preliminar para redação científica; não é parecer
jurídico de patenteabilidade ou liberdade de operação

## 1. Conclusão executiva

A transformação

\[
\Gamma(\omega;Z_0)=\frac{Z(\omega)-Z_0}{Z(\omega)+Z_0},
\qquad
Z=Z_0\frac{1+\Gamma}{1-\Gamma}
\]

é a transformação bilinear clássica entre impedância normalizada e coeficiente
de reflexão usada no diagrama de Smith. Ela não é nova e não deve ser apresentada
como invenção do KAIRIS. Também existe uso anterior de diagramas de Smith, de
coeficientes de reflexão e de trajetórias de impedância dependentes da frequência
em instrumentação, baterias, sensores e na própria literatura de EIS.

A hipótese de novidade cientificamente defensável é mais estreita: a ESC propõe
uma **estrutura de referência eletroquímica e extração quantitativa de
descritores**, aplicada de forma reproduzível a uma transformação clássica.
Essa estrutura compreende quatro referências G1--G4 ligadas a DRT, geometria,
condutividade e pontos característicos do espectro; retenção explícita da
frequência; métricas de trajetória; regras de confiabilidade e abstenção; e
integração transparente com Lin--KK, DRT e GSF/RSF.

## 2. Escopo e estratégia de busca

Foram consultadas buscas gerais de literatura, páginas de editoras, repositórios
acadêmicos e Google Patents. Combinações usadas incluíram:

- `Smith chart electrochemical impedance spectroscopy`;
- `electrochemical impedance reflection coefficient Smith chart battery`;
- `Smith chart impedance frequency trajectory electrochemical`;
- `patent Smith chart electrochemical impedance`;
- `new graph electrochemical impedance Smith chart`;
- o nome antigo e o nome novo do método, com e sem hífen.

Uma busca sistemática posterior deve repetir as consultas em Scopus, Web of
Science, IEEE Xplore, Espacenet, WIPO Patentscope, Google Scholar e bases de
teses, registrando consulta, data, número de resultados e decisão de inclusão.

## 3. Anterioridade material localizada

| Fonte | Evidência relevante | Consequência para a alegação |
|---|---|---|
| P. H. Smith, *Transmission Line Calculator*, *Electronics* 12 (1939), 29--31 | origem histórica do diagrama e da normalização de impedância | a cartografia de Smith e sua transformação não podem ser reivindicadas |
| J. F. White, *The Smith Chart*, 2003, DOI 10.1002/0471474827.ch5 | deriva a transformação bilinear e discute referência arbitrária, frequência e uso sem linhas de transmissão | nem referência arbitrária nem trajetória em frequência bastam para novidade |
| Z. Siroma e K. Kuratani, *Electrochimica Acta* 509 (2025) 145305, DOI 10.1016/j.electacta.2024.145305 | lista Smith charts entre representações já utilizadas em EIS | não usar “primeiro diagrama de Smith para EIS” |
| T. F. Landinger, G. Schwarzberger e A. Jossen, *Journal of Power Sources* 488 (2021) 229463, DOI 10.1016/j.jpowsour.2021.229463 | mede impedância de células com VNA e usa exatamente a relação entre \(S_{11}\), \(Z_0\) e \(Z_{bat}\) | coeficiente de reflexão aplicado a uma bateria também possui anterioridade |
| US8056034B1 | define o Smith chart como representação de impedância/coefficientes em função da frequência e discute passividade e causalidade | frequência, passividade e trajetória no disco não são isoladamente novas |
| CN115201570B | sistema de varredura de impedância e visualização de trajetórias no Smith chart, com pontos de frequência e extração de características | varredura, marcação de frequência e extração genérica de características têm anterioridade |
| WO2024249876A2 | sensor eletroquímico/NFC com Smith chart e coeficiente de reflexão | o simples contexto eletroquímico ou de biossensor não diferencia a ESC |

## 4. Matriz de alegações

### Alegações que não devem ser feitas

- “nova transformação de Smith”;
- “primeiro uso do coeficiente de reflexão em eletroquímica, baterias ou EIS”;
- “primeiro gráfico de impedância eletroquímica no disco unitário”;
- “prova de mecanismo eletroquímico a partir da posição no diagrama”;
- “passividade validada apenas porque \(|\Gamma|\leq1\)”, sem considerar as
  hipóteses sobre \(Z_0\), convenção de sinais e qualidade do espectro.

### Alegações provisoriamente defensáveis, ainda dependentes de validação

1. estrutura de quatro referências eletroquímicas pré-especificadas G1--G4;
2. vínculo rastreável entre referências, DRT, geometria e condutividade;
3. descritores quantitativos e frequenciais da trajetória, em vez de inspeção
   apenas visual;
4. política explícita de singularidade, baixa confiabilidade e abstenção;
5. avaliação da sensibilidade à referência e da estabilidade a ruído,
   truncamento e densidade de pontos;
6. integração e ablação em um protocolo multivista reprodutível;
7. implementação autônoma equivalente ao módulo integrado.

Esses itens constituem uma **hipótese de novidade do conjunto**, não a certeza
de que nenhum trabalho anterior combinou subconjuntos semelhantes.

## 5. Formulação recomendada para artigo

> Electrochemical Spectral Cartography (ESC) is a frequency-resolved
> electrochemical reference and feature-extraction framework built on the
> classical Smith impedance-to-reflection-coefficient transform. We claim no
> novelty for the bilinear transform itself. The proposed contribution is the
> pre-specified G1--G4 reference scheme, its provenance-aware abstention rules,
> quantitative trajectory descriptors, and validation as an independent and
> integrated EIS analysis module.

Versão curta em português:

> A ESC é uma estrutura de referências e descritores eletroquímicos resolvidos
> em frequência, construída sobre a transformação bilinear clássica de Smith.
> A novidade proposta está no esquema G1--G4, nas regras de confiabilidade e
> abstenção e na validação dos descritores, não na transformação matemática.

## 6. Experimentos necessários antes de um artigo independente

1. provar numericamente a inversão fora dos pontos singulares;
2. demonstrar o domínio mapeado para referências reais positivas e declarar o
   comportamento para referências complexas;
3. medir sensibilidade de cada descritor a \(Z_0\), ruído, truncamento e
   reamostragem;
4. comparar G1--G4 com referências convencionais como \(R_s\), \(R_\infty\),
   mediana de \(|Z|\) e normalização fixa;
5. testar se os descritores acrescentam informação além de Nyquist/Bode e dos
   parâmetros que originaram cada \(Z_0\);
6. usar corpus sintético com verdade conhecida e conjuntos experimentais
   externos;
7. pré-especificar endpoints e correção para comparações múltiplas;
8. relatar resultados negativos e casos em que a referência não é identificável.

## 7. Fontes verificadas

- Smith (1939), cópia histórica: https://electronicsandbooks.com/edt/manual/Magazine/E/Electronics%20US/30s/Electronics-1939-01%20c20160310%20%5B70%5D.pdf
- White (2003): https://doi.org/10.1002/0471474827.ch5
- Siroma e Kuratani (2025): https://doi.org/10.1016/j.electacta.2024.145305
- Landinger, Schwarzberger e Jossen (2021): https://doi.org/10.1016/j.jpowsour.2021.229463
- US8056034B1: https://patents.google.com/patent/US8056034B1/en
- CN115201570B: https://patents.google.com/patent/CN115201570B/en
- WO2024249876A2: https://patents.google.com/patent/WO2024249876A2/en

