# Plano de validação científica do KAIRIS — versão 1.0

**Nome oficial:** KAIRIS — Kramers–Kronig-Assessed Impedance, Relaxation, and
Integrated Spectroscopy.

**Estado:** aprovado e congelado para validação retrospectiva e de desenvolvimento

**Aprovação do pesquisador responsável:** 3 de novembro de 2026

**Identificador público do congelamento:** tag Git `validation-plan-v1.0`

**LLM na análise primária:** desativada

## 1. Escopo do congelamento

Este plano governa três produtos científicos relacionados, mas analiticamente
separáveis:

1. **KAIRIS integrado**, mantido na branch `main`, que executa EIS → DRT → GSF →
   ESC → síntese;
2. **GSF independente**, mantido na branch `standalone/gsf`, congelada inicialmente
   no commit `26c50e1f3f922ccabfec3e8adaf2c7067af5af55`;
3. **ESC independente**, mantido na branch `standalone/esc`, congelada inicialmente
   no commit `311f0c072193c1a36b289d63b0f4228f84e3d4eb`.

GSF e ESC são métodos originais do autor do KAIRIS. A disponibilização autônoma
não os remove do protocolo integrado nem transforma suas saídas em evidência
causal de mecanismos eletroquímicos.

O congelamento v1.0 fixa perguntas, endpoints, métricas, limiares e política de
mudanças para o corpus já conhecido. Ele não converte retrospectivamente esses
dados em holdout confirmatório.

## 2. Declaração de transparência

Os 198 espectros do corpus atual e parte de seus resultados já foram examinados
durante o desenvolvimento. Portanto, eles serão tratados como validação
retrospectiva, desenvolvimento e caracterização de falhas. Não serão descritos no
artigo como conjunto confirmatório intocado.

O registro público no GitHub documenta o congelamento temporal desta versão, mas
não será apresentado como equivalente a um pré-registro confirmatório no OSF. O
futuro estudo externo só será chamado de pré-registrado depois que origem, tamanho,
seleção, exclusões e análise forem depositados antes da abertura dos resultados.

## 3. Perguntas e hipóteses congeladas

### 3.1 KAIRIS integrado

**Pergunta principal:** o KAIRIS produz, de forma reproduzível e auditável,
descritores complementares por Lin-KK, DRT, GSF e ESC, sinalizando divergência ou
insuficiência de evidência sem depender de uma LLM?

**H1 — integridade:** todos os espectros declarados compatíveis devem gerar
artefatos completos ou uma falha explícita e rastreável, nunca uma saída parcial
tratada como válida.

**H2 — recuperação sintética:** em referências simples com verdade conhecida, o
KAIRIS deve recuperar R∞ e tempos de relaxação dentro dos limites da seção 6.

### 3.2 GSF independente

**H3 — equivalência modular:** para os mesmos vetores EIS e a mesma configuração,
o comando independente deve produzir os mesmos descritores numéricos e regime que
o GSF do pipeline integrado.

**H4 — invariância de escala:** uma multiplicação positiva e uniforme da
impedância não deve alterar as grandezas normalizadas do GSF além da tolerância
numérica congelada.

### 3.3 ESC independente

**H5 — equivalência modular:** para os mesmos vetores EIS e referências Z₀, o ESC
independente deve produzir a mesma transformação que o Agente 4 integrado.

**H6 — consistência algébrica:** fora dos pontos singulares declarados, a
transformação inversa deve reconstruir a impedância original dentro da tolerância
numérica congelada.

As hipóteses H3–H6 testam implementação, equivalência e propriedades matemáticas.
Elas não validam, isoladamente, a interpretação eletroquímica de GSF ou ESC.

## 4. Alegações permitidas e proibidas

O estudo poderá avaliar se o KAIRIS e seus módulos independentes:

1. importam formatos heterogêneos de EIS;
2. executam sem falhas silenciosas de infraestrutura;
3. recuperam referências simples conhecidas em espectros sintéticos;
4. produzem resultados numericamente equivalentes nos ambientes declarados;
5. identificam e relatam desacordos entre observáveis;
6. preservam proveniência, abstinência e resultados inconclusivos;
7. funcionam sem LLM em Windows, Linux e macOS.

Não será alegado, sem evidência adicional, que:

- existe um único circuito equivalente identificável para cada espectro;
- toda divergência entre agentes representa erro;
- DRT, GSF ou ESC identificam causalmente um mecanismo eletroquímico;
- o regime GSF é uma verdade mecanística por si só;
- uma escolha de Z₀ no ESC é correta apenas porque produz uma geometria regular;
- a interpretação da LLM substitui avaliação especializada;
- os 198 espectros constituem validação externa independente.

## 5. Dados e prevenção de vazamento

| Conjunto | Papel no estudo |
|---|---|
| 72 sintéticos KAIRIS | desenvolvimento, regressão e caracterização de falhas |
| AutoECM 45 treino | desenvolvimento e comparações exploratórias |
| AutoECM 27 teste | benchmark retrospectivo; não é mais holdout intocado |
| Zenodo NMC811, 54 células | avaliação externa retrospectiva de um domínio |
| Dados futuros independentes | validação confirmatória prospectiva |

Espectros correlacionados da mesma célula, campanha, artigo ou lote permanecerão no
mesmo grupo. Pontos de frequência nunca serão divididos entre treino e teste. Uma
execução do mesmo espectro em `main`, `standalone/gsf` e `standalone/esc` representa
uma unidade experimental, não três observações independentes.

## 6. Endpoints primários do KAIRIS integrado

Os critérios executáveis estão em `config/validation_acceptance_v1.json`.

### 6.1 Integridade e proveniência

- 100% das amostras devem possuir JSON consolidado e relatório HTML;
- 100% dos hashes de entrada devem coincidir com o manifesto;
- 100% dos artefatos da release devem registrar árvore Git limpa e commit atual;
- nenhum resultado pode ser reutilizado na execução de release.

### 6.2 Referência sintética ideal de Randles

Para os seis espectros `randles_rc`:

- aprovação Lin-KK em pelo menos 95%;
- exatamente um pico DRT em pelo menos 95%;
- erro relativo mediano de R∞ no máximo 2%;
- pior erro relativo de R∞ no máximo 5%;
- erro mediano de localização do pico no máximo 0,10 década em log10(τ);
- pior erro de localização do pico no máximo 0,20 década em log10(τ).

Esses limiares foram escolhidos após contato com o corpus e são gates de
desenvolvimento retrospectivos, não endpoints confirmatórios prospectivos.

### 6.3 Recuperação multirrelaxação e domínio operacional

O script `scripts/analyze_synthetic_recovery.py` fará correspondência um a um por
erro mínimo em log10(τ) para Randles, ZARC simples, duplo e triplo. Serão relatados
número de picos, fração de processos pareados, erro de τ e erro de R∞.

O script `scripts/run_robustness_benchmark.py` avaliará separação entre relaxações,
ruído e truncamento de frequência. Famílias difusivas, distribuídas, indutivas,
com deriva ou outliers não serão forçadas a uma verdade de picos DRT.

R∞ primário só será aceito quando os oito pontos de maior frequência satisfizerem
fase absoluta no ponto máximo ≤7° e amplitude relativa de Re(Z) ≤10%. A estimativa
assintótica secundária não substituirá esse endpoint nem será usada no ESC G4.
Múltiplos picos DRT só serão chamados de numericamente resolvidos quando a menor
separação atingir 1,3 década no benchmark atual.

## 7. Endpoints primários do GSF independente

Os limiares executáveis estão em
`config/standalone_validation_acceptance_v1.json`.

1. **Importação:** 100% dos arquivos que o KAIRIS integrado declara compatíveis
   devem ser aceitos pelo GSF independente ou gerar erro explícito equivalente.
2. **Equivalência:** posições de NaN devem coincidir; valores finitos de `x_n`,
   `y_n`, `q`, `alpha`, `kphi`, `gradient`, `I_crit` e `f_Icrit` devem concordar com
   `rtol=1e-10` e `atol=1e-12`; `regime_gsf` deve ser idêntico.
3. **Invariância:** ao multiplicar simultaneamente Re(Z) e Im(Z) por 0,1, 10 e
   100, os descritores normalizados devem permanecer dentro das mesmas tolerâncias.
4. **Completude:** toda análise concluída deve gerar JSON e os três SVGs esperados.

Não será exigida identidade byte a byte dos SVGs, pois metadados e versões do
renderizador podem variar. Sensibilidade à densidade de pontos, remoção de
frequências e ruído será análise secundária descritiva.

## 8. Endpoints primários do ESC independente

1. **Política de referência:** toda referência Z₀ deve ser fornecida e registrada
   explicitamente; o módulo independente não inferirá automaticamente seu
   significado físico.
2. **Equivalência:** para EIS e Z₀ idênticos, Γ, centróide, média de |Γ|, ponto de
   baixa frequência e flags devem coincidir com o Agente 4 em `rtol=1e-10` e
   `atol=1e-12`.
3. **Inversão:** para pontos com `|1−Γ| ≥ 1e-12`, a reconstrução
   `Z = Z₀(1+Γ)/(1−Γ)` terá erro relativo máximo ≤1e-10.
4. **Passividade matemática:** quando Z₀ for real e positivo e Re(Z) ≥0 dentro da
   tolerância, deverá valer `|Γ| ≤ 1+1e-10`.
5. **Completude:** toda análise concluída deve gerar JSON e HTML interativo com a
   frequência preservada em cada ponto.

A sensibilidade a `0,5×`, `1×` e `2×` uma referência nominal será relatada, mas não
escolherá automaticamente o melhor Z₀ e não será gate primário.

## 9. Endpoints descritivos e revisão humana

Serão relatados sem transformar automaticamente divergência em falha:

- taxa Lin-KK por origem e família;
- número de picos e resíduos DRT;
- regimes DRT e GSF e frequência de divergência;
- descritores GSF por origem, sem rótulo causal automático;
- comportamento ESC para cada Z₀ declarado;
- tempo, memória, falhas, abstenções e mensagens de cautela.

A revisão seguirá `paper/BLINDED_REVIEW_PROTOCOL_v1.md`. Revisores não verão
resultados integrados nem independentes antes do congelamento das anotações. ESC
será comparado à avaliação humana apenas quando houver uma hipótese física de Z₀
definida antes da abertura dos resultados.

## 10. Plano estatístico

- gates determinísticos serão relatados como aprovação/falha e com seus valores;
- estimativas contínuas usarão mediana, intervalo interquartil e IC de 95% por
  bootstrap com 2.000 reamostragens e semente `20261103`;
- o bootstrap será feito por célula, estudo ou campanha, nunca por ponto de
  frequência quando houver agrupamento;
- classificações com referência adequada usarão balanced accuracy, macro-F1,
  sensibilidade, especificidade, valores preditivos, matriz de confusão e taxa de
  abstenção;
- ausências, indeterminações e abstenções terão denominador explícito e não serão
  silenciosamente convertidas em erros ou acertos;
- análises de subgrupo serão secundárias, identificadas como exploratórias e sem
  ajuste retrospectivo dos endpoints primários.

Todos os gates primários aplicáveis deverão passar. Não haverá compensação entre
um gate reprovado e outro aprovado nem seleção posterior do resultado mais
favorável entre pipeline e módulos independentes.

## 11. LLM

A análise primária será executada com LLM desativada. Ollama será uma análise
secundária, registrando modelo, quantização, prompt, temperatura, memória,
exemplos e intervenção humana. Nenhuma amostra confirmatória poderá entrar em
memória, few-shot ou fine-tuning antes do encerramento da análise.

## 12. Execução e ambientes

A validação candidata partirá de commit limpo, tag exata e saída vazia:

```powershell
python scripts/run_release_validation.py `
  --output output/validation_release_v1 `
  --require-tag
```

O KAIRIS integrado e os dois comandos independentes serão testados em Python 3.12
nos runners atuais de Windows, Ubuntu e macOS. Diferenças numéricas acima das
tolerâncias congeladas serão falhas de portabilidade.

## 13. Controle de mudanças e desvios

Depois da tag `validation-plan-v1.0`:

- nenhum endpoint, limiar, exclusão ou classificação primária poderá ser alterado
  sem nova versão do plano;
- correções de bug serão permitidas, mas registradas em
  `paper/DEVIATIONS_LOG_v1.md`, com impacto e reexecução integral dos testes;
- mudanças anteriores à abertura do conjunto confirmatório gerarão versão 1.1;
- mudanças posteriores à abertura serão desvios, nunca chamadas de
  pré-especificadas;
- resultados desfavoráveis não autorizam remoção de amostras ou troca de endpoint.

## 14. Registro público e validação confirmatória futura

O pacote v1.0 será publicado como tag e release no GitHub, acompanhado de hashes.
Esse registro é o congelamento público do estudo retrospectivo. Uma cópia idêntica
deverá ser depositada no OSF; até isso ocorrer, o estado será descrito como
**publicly frozen**, não como **OSF preregistered**.

Antes de abrir o futuro conjunto externo deverão ser adicionados, em um adendo
pré-registrado: domínio, origem independente, tamanho amostral justificado, unidade
experimental, critérios de inclusão/exclusão, tratamento de replicatas, referência
humana ou sintética, política de ausências e local público do registro.

## 15. Decisão de aprovação

O pesquisador responsável aprovou em 3 de novembro de 2026 a pergunta principal,
as alegações permitidas, os gates retrospectivos, a política de abstinência, o
plano estatístico, a revisão cega e a inclusão dos ramos GSF e ESC independentes.
Detalhes ainda desconhecidos do futuro conjunto externo não estão aprovados por
antecipação e deverão constar de adendo antes do acesso aos resultados.
