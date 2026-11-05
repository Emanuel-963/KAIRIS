# Busca de anterioridade e formulação de novidade — GSF/RSF v1

**Família proposta:** Ratio Spectral Field (RSF)  
**Subfamília atual:** Golden Spectral Field (GSF)  
**Data da busca:** 4 de novembro de 2026  
**Estado:** levantamento preliminar para refinamento científico; não é parecer
jurídico de patenteabilidade

## 1. Conclusão executiva

As expressões exatas “Ratio Spectral Field” e “Golden Spectral Field” não foram
localizadas nas consultas realizadas em combinação com EIS e impedância. Isso
apoia a distintividade dos nomes, mas não prova novidade do método.

Há anterioridade substancial para componentes matemáticos e analíticos próximos:
normalização de espectros de impedância, módulos no plano complexo, inclinações
locais, derivadas em \(\log f\), expoentes de CPE, auto-similaridade, análise
fractal e extração model-free de características. Logo, a eventual contribuição
deve ser formulada como uma construção conjunta, com hipóteses e desempenho
validados, e não como invenção de normalização, logaritmos, derivadas ou do uso
do número de ouro.

## 2. Definição atual e equivalência entre bases

No código atual,

\[
x_n=\frac{\operatorname{Re}Z_n}{\max\operatorname{Re}Z},\quad
y_n=\frac{|\operatorname{Im}Z_n|}{\max|\operatorname{Im}Z|},\quad
q_n=\sqrt{x_n^2+y_n^2},
\]

e

\[
\alpha_b(n)=\frac{\ln(q_n/q_{n-1})}{\ln b}.
\]

Para qualquer base fixa válida \(b>0\), \(b\ne1\), a troca de base apenas
reescalona o mesmo numerador. Em particular,

\[
\alpha_{\varphi^k}=\frac{1}{k}\alpha_\varphi,
\qquad
\alpha_{1/\varphi}=-\alpha_\varphi.
\]

Assim, \(\varphi\), \(\varphi^2\), \(\varphi^3\) e \(1/\varphi\) não geram
informação independente nessa definição: mudam escala ou sinal. Bases como
\(2\varphi\) e \(3\varphi\) também multiplicam todos os expoentes por uma
constante. O descritor atual \(k_\varphi=\varphi q\) é igualmente uma
reescalagem de \(q\).

Isso não impede o uso de uma família áurea como sistema de coordenadas, mas
impede afirmar que cada base revela, por si só, um fenômeno físico diferente.
Tal diferença exigiria outra operação matemática ou evidência preditiva que não
seja removida por uma transformação linear de escala.

## 3. Problema científico prioritário identificado

O \(\alpha\) atual usa pontos consecutivos no numerador, mas não divide pela
separação entre suas frequências. Portanto, ele depende da densidade e da
irregularidade da grade de aquisição. Reamostrar o mesmo espectro pode alterar
\(\alpha\) e os limiares de regime sem alterar a física.

Uma referência de comparação natural é o expoente base-free

\[
\beta_n=\frac{\Delta\ln q}{\Delta\ln f},
\]

calculado com diferenças robustas numa grade de \(\ln f\). Uma generalização
RSF cientificamente forte deve:

1. separar descritores invariantes da escolha de base das coordenadas apenas
   reescaladas;
2. demonstrar estabilidade à densidade de pontos e ao reamostramento;
3. definir se a família áurea acrescenta uma estrutura operacional além da
   troca de base;
4. recalibrar qualquer limiar de classificação em dados de desenvolvimento e
   congelá-lo antes do teste externo.

O código científico não foi alterado nesta busca, pois essa mudança afetaria
endpoints já congelados. Ela deve ser testada primeiro como análise de
sensibilidade e registrada como nova versão do método.

## 4. Anterioridade material localizada

| Fonte | Evidência relevante | Consequência para a alegação |
|---|---|---|
| Siroma e Kuratani, *Electrochimica Acta* 509 (2025) 145305, DOI 10.1016/j.electacta.2024.145305 | propõe gráficos baseados em derivadas de \(Z\) em relação a \(\log f\), incluindo fase e magnitude locais | derivadas locais e descritores frequenciais não são isoladamente novos |
| Lenz, Zabel e Franzreb, *Frontiers in Materials* 7 (2020) 229 | introduz Nyquist Incline Frequency, a inclinação local do Nyquist contra frequência | inclinação local associada a frequência tem anterioridade em EIS poroso |
| *Self-Similar Interfacial Impedance of Electrodes in High Conductivity Media*, *Analytical Chemistry* (2018), DOI 10.1021/acs.analchem.7b03753 | estuda auto-similaridade de impedância e frequência normalizadas | normalização e auto-similaridade não bastam para novidade |
| *Inferring fractal dimension of rough/porous surfaces*, *Applied Surface Science* (2009) | relaciona expoente de CPE e dimensão fractal | expoentes fracionários já possuem interpretação e controvérsias anteriores |
| artigo sobre Ti--6Al--4V em PBS, *Corrosion and Materials Degradation* 5 (2024) | usa \(|d\log|Z_j|/d\log f|\) como estimativa de expoente | derivada log--log do módulo já é empregada em análise eletroquímica |
| Martinez et al., *Scientific Reports* 16 (2026) 5833, DOI 10.1038/s41598-026-35621-3 | compara normalizações e extração não supervisionada de características de EIS | o benefício da normalização precisa ser testado contra alternativas |
| Y. Liu et al., análise de vida de revestimentos (2017) | usa a taxa discreta \(\Delta\log|Z|/\Delta\log f\) como característica | diferenças logarítmicas discretas têm anterioridade aplicada |

## 5. Alegações que não devem ser feitas

- “primeiro expoente local de um espectro EIS”;
- “primeira normalização model-free de EIS”;
- “\(\varphi\) produz informação nova por ser o número de ouro”;
- “\(\varphi^2\), \(\varphi^3\) e \(1/\varphi\) detectam mecanismos distintos”
  quando a fórmula apenas reescala \(\alpha\);
- “classificação mecanística” sem validação externa e sem análise de
  identificabilidade;
- equivaler \(\alpha_{GSF}\) ao expoente CPE sem derivação e teste.

## 6. Formulação de novidade recomendada

Hipótese provisória:

> The Ratio Spectral Field (RSF) is a parameterized, model-free family of
> normalized complex-impedance trajectory descriptors. The Golden Spectral
> Field (GSF) is its golden-ratio coordinate subfamily. Novelty is not claimed
> for normalization, logarithmic slopes, or the golden ratio individually;
> the proposed contribution is their pre-specified joint construction,
> frequency-resolved criticality descriptors, uncertainty policy, and
> validation across synthetic and external electrochemical spectra.

Formulação em português:

> O RSF é uma família parametrizada e independente de circuito de descritores
> para trajetórias normalizadas de impedância complexa; o GSF é sua subfamília
> de coordenadas áureas. A novidade proposta não reside isoladamente na
> normalização, na inclinação logarítmica ou no número de ouro, mas na construção
> conjunta, nos descritores críticos resolvidos em frequência e em sua validação.

## 7. Programa mínimo antes do artigo GSF/RSF

1. formalizar RSF\((b)\) e provar todas as equivalências de mudança de base;
2. introduzir e comparar \(\beta=\mathrm d\ln q/\mathrm d\ln f\), independente
   de base e da densidade de amostragem;
3. executar ablação de \(q\), \(\alpha_b\), \(k_b\), \(S\) e
   \(I_{crit}\), evitando que uma simples reescala conte como novo atributo;
4. testar invariância à escala de impedância, ordenação, interpolação, número de
   pontos por década e truncamento de frequência;
5. comparar com inclinação de Bode, NIF, expoente CPE, derivada de Bode e
   características normalizadas convencionais;
6. usar circuitos sintéticos e modelos distribuídos com parâmetros conhecidos;
7. reservar sistemas experimentais externos por estudo/célula, sem vazamento;
8. estimar incerteza por bootstrap agrupado e calibrar uma classe inconclusiva;
9. congelar qualquer nova versão e preservar a análise GSF v1 como referência;
10. verificar se a família áurea melhora algum endpoint após normalização das
    escalas; se não melhorar, apresentá-la como coordenada interpretável, não
    como fonte independente de informação.

## 8. Fontes verificadas

- Siroma e Kuratani (2025): https://doi.org/10.1016/j.electacta.2024.145305
- Lenz, Zabel e Franzreb (2020), NIF: https://doi.org/10.3389/fmats.2020.00229
- Self-similar impedance (2018): https://doi.org/10.1021/acs.analchem.7b03753
- Revisão/tutorial de EIS: https://doi.org/10.1021/acsmeasuresciau.2c00070
- Normalização e clustering de EIS (2026): https://doi.org/10.1038/s41598-026-35621-3
- Derivada logarítmica em espectrometria dielétrica: https://doi.org/10.1088/0957-0233/14/9/401

