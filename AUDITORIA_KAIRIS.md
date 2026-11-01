# Auditoria técnica e funcional do KAIRIS

**Data da auditoria:** 1 de novembro de 2026  
**Escopo:** código científico, agentes, orquestração, painel web, relatórios, configuração, instalação, portabilidade, Docker, testes e riscos operacionais.  
**Natureza do documento:** descrição do sistema existente e auditoria de implementação. Este arquivo não substitui validação metrológica, revisão por pares ou qualificação do método científico.

## 1. Resumo executivo

O KAIRIS é um pipeline local para análise de espectroscopia de impedância eletroquímica sem ajuste explícito de circuito equivalente. Ele recebe espectros EIS em arquivos de texto, executa cinco agentes em sequência e gera métricas estruturadas, figuras SVG e um relatório HTML interativo por amostra.

O fluxo implementado é:

```text
arquivo EIS
   ↓
Agente 1 — leitura, normalização e controle de qualidade
   ↓
Agente 2 — distribuição de tempos de relaxação e referências Z₀
   ├───────────────┐
   ↓               ↓
Agente 3 — GSF    Agente 4 — ESC usando os Z₀ do Agente 2
   └───────────────┘
           ↓
Agente 5 — síntese por regras, LLM opcional e relatório HTML
```

### Situação verificada

- O pipeline principal está implementado e os cinco agentes funcionam em sequência.
- A execução pode ocorrer pela linha de comando, pelo monitoramento contínuo ou pelo painel web local.
- Os formatos de texto avaliados, incluindo variantes tabuladas, separadas por ponto e vírgula, com vírgula decimal e cabeçalhos alternativos, são reconhecidos.
- A saída usa identificadores derivados do caminho relativo, evitando colisão entre arquivos homônimos em subpastas.
- O modo sem LLM é completo; Ollama e OpenAI são complementos opcionais do Agente 5.
- Os 25 testes automatizados existentes passaram após as correções registradas nesta auditoria.
- A verificação de pré-requisitos passou em Windows com Python 3.12.14, 15,9 GB de RAM, dependências Python disponíveis e Ollama detectado.
- Existem 50 relatórios no diretório de saída no momento da auditoria. Esse total inclui execuções de validação além do lote científico e, portanto, não deve ser interpretado como número de amostras únicas.
- O projeto possui repositório Git local inicializado para rastreabilidade das versões.

### Conclusão

O KAIRIS está operacional como ferramenta local de análise exploratória e geração de relatórios. O indicador **Spectral Smoothness (local residue)** permanece como diagnóstico local separado. A validação integral foi acrescentada pelo método Lin-KK de Schönleber, com base compatível com Kramers-Kronig, seleção por μ e critérios explícitos de resíduo. A proveniência por amostra registra hash, timestamp, versões e configuração efetiva. Os principais pontos que ainda exigem atenção antes de tratar seus resultados como método científico qualificado são: faltam conjuntos experimentais certificados para validação externa e o painel não deve ser exposto a redes não confiáveis.

## 2. Estrutura do projeto

O projeto possui aproximadamente 2.409 linhas em 20 arquivos Python, além do frontend, scripts de instalação, configuração, testes e infraestrutura de contêiner.

| Área | Responsabilidade |
|---|---|
| `agents/` | Implementações independentes dos cinco agentes científicos e do orquestrador |
| `core/` | Leitura EIS, DRT, GSF, ESC, configuração e construção do relatório |
| `config/` | Parâmetros operacionais e científicos do protocolo |
| `models/` | Contexto científico fornecido à LLM opcional |
| `web/` | Template, estilo e JavaScript do painel local |
| `scripts/` | Instalação e inicialização em Windows e Linux |
| `tests/` | Testes unitários, integração do painel e verificações visuais auxiliares |
| `data/input/` | Entrada padrão dos espectros |
| `output/metrics/` | JSONs intermediários e consolidados |
| `output/figures/` | Gráficos GSF estáticos em SVG |
| `output/reports/` | Relatórios HTML finais |
| `run_pipeline.py` | Orquestração por linha de comando e modo contínuo |
| `web_app.py` | Servidor Flask e gerenciamento do subprocesso do pipeline |
| `setup_kairis.py` | Assistente multiplataforma de instalação e configuração |
| `Dockerfile` e `compose.yaml` | Execução em contêiner, sem LLM por padrão |

## 3. Fluxo dos dados e artefatos

Cada espectro percorre os cinco agentes de forma síncrona. Uma falha em uma amostra é registrada, mas não impede o processamento das demais amostras do diretório.

### Identidade da amostra

O identificador é criado a partir do caminho relativo ao diretório de entrada. Segmentos são unidos por `__` e caracteres inadequados são normalizados. Assim, arquivos como `celula_1/amostra.txt` e `celula_2/amostra.txt` produzem saídas distintas.

### Artefatos gerados

Para cada amostra, o pipeline pode produzir:

- JSON do Agente 1 com dados EIS normalizados e controle de qualidade;
- JSON do Agente 2 com grade DRT, picos e referências Z₀;
- JSON do Agente 3 com métricas GSF e caminhos das figuras;
- três SVGs estáticos do GSF: α, kφ e gradiente espectral;
- JSON do Agente 4 com os quatro grupos ESC;
- JSON consolidado do Agente 5;
- relatório HTML final;
- registros de execução em `output/pipeline.log` e, quando iniciado pelo painel, `output/web_runner.log`.

Os JSONs convertem valores NumPy para tipos serializáveis e transformam valores não finitos em `null`. JSON, SVG e HTML são gravados em arquivo `.tmp` no mesmo diretório, sincronizados com `fsync` e promovidos com `os.replace`, evitando artefatos finais parciais em caso de interrupção.

## 4. Agente 1 — EIS

### O que faz

O Agente 1 lê o arquivo, identifica as colunas de frequência, parte real e parte imaginária da impedância, normaliza sinais e unidades esperadas, remove linhas inválidas e organiza os pontos da maior para a menor frequência.

### Compatibilidade de entrada

O carregador aceita:

- codificações `UTF-8-SIG`, `UTF-8`, a codificação configurada e `Latin-1`;
- separadores tabulação e ponto e vírgula;
- números com ponto ou vírgula decimal;
- cabeçalhos comuns de frequência e impedância, incluindo variantes com símbolos Ω e notações de parte imaginária negativa;
- arquivos com linhas de metadados antes do cabeçalho tabular.

São descartadas linhas não numéricas, frequências não positivas e frequências duplicadas. Quando a coluna de origem representa `-Im(Z)`, o valor é convertido para a convenção complexa usada internamente.

### Saídas científicas

- número de pontos válidos;
- limites de frequência;
- arrays de frequência, Re(Z), Im(Z), magnitude e fase;
- porcentagem de resíduo local acima do limiar;
- indicador `spectral_smooth`;
- classificação morfológica heurística: arco capacitivo, cauda difusiva, comportamento misto ou indeterminado.

### Limitação importante

Spectral Smoothness reconstrói cada ponto interior a partir dos vizinhos no eixo de log-frequência e mede um resíduo complexo local. É explicitamente um indicador de suavidade local, não uma validação integral de Kramers-Kronig nem uma prova completa de causalidade, linearidade e estabilidade do espectro. Essa ressalva aparece no código e no relatório HTML.

`smoothness_threshold_permissive` ainda participa tanto do limiar de resíduo permissivo quanto da fração máxima de falhas usada para definir `spectral_smooth`. Esses conceitos deveriam ter parâmetros separados para evitar ambiguidade dimensional e facilitar calibração.

### Validação Lin-KK

Separadamente, o Agente 1 executa uma validação linear Kramers-Kronig baseada em R₀, elementos RC com tempos log-distribuídos e indutância serial. O ajuste complexo é linear nos parâmetros. O número de elementos cresce até satisfazer simultaneamente o corte de μ, o RMSE normalizado e a fração máxima de pontos fora do limite. O máximo efetivo é limitado para manter o sistema sobreterminado.

As saídas incluem `lin_kk_valid`, convergência, M, máximo M efetivo, μ, RMSE, resíduo máximo, porcentagem de falhas, impedância ajustada e resíduos real/imaginário por frequência. Uma aprovação significa compatibilidade com a base Lin-KK dentro dos limites configurados; não substitui o controle experimental de linearidade, estabilidade e causalidade.

## 5. Agente 2 — DRT

### O que faz

O Agente 2 resolve uma distribuição não negativa de tempos de relaxação por regularização de Tikhonov no domínio logarítmico de τ.

### Implementação

- Cria uma grade de τ derivada da faixa de frequência; o padrão é 100 pontos.
- Usa o núcleo complexo `1 / (1 + jωτ)`.
- Aplica regularização de segunda diferença para favorecer suavidade.
- Resolve mínimos quadrados com restrição de não negatividade por `scipy.optimize.lsq_linear`.
- Avalia 25 valores de λ entre `10⁻⁸` e `10²`.
- Seleciona λ por curvatura discreta da curva L.
- Detecta picos com `scipy.signal.find_peaks` e proeminência relativa configurável.
- Integra a área de cada pico entre mínimos vizinhos.

### Referências Z₀ produzidas

| Grupo | Referência operacional |
|---|---|
| G1 | Área do primeiro pico, interpretada como Rct; usa área total se não houver pico |
| G2 | Impedância complexa no ponto em que Re(Z) é mais próxima de `|Im(Z)|` |
| G3 | Módulo de Z próximo da frequência característica do primeiro pico |
| G4 | `L/(κA)` quando o nome do arquivo corresponde a um eletrólito configurado; R∞ como fallback explícito |

### Classificação

O regime DRT é classificado como dominado por cinética, dominado por difusão ou misto a partir do tempo do pico principal e da contribuição da cauda.

### Limitações científicas

- R∞ é aproximada pelo ponto real de maior frequência, não extrapolada nem ajustada.
- Rct é uma interpretação operacional da área do primeiro pico; picos sobrepostos, truncamento da faixa ou regularização excessiva podem alterar esse valor.
- A escolha de λ depende de uma curva L discreta e não apresenta intervalo de incerteza.
- Não há propagação de incerteza, análise de sensibilidade ou bootstrap.
- O parâmetro `drt_lambda_method` existe na configuração, mas a implementação sempre usa curva L.
- A integração usa `numpy.trapz` em NumPy 1.x e uma fórmula trapezoidal equivalente nas versões recentes que removeram esse alias, mantendo `numpy>=1.24`.
- A seleção de condutividade depende da identificação do eletrólito no nome do arquivo. O resultado registra a origem e o eletrólito; nomes sem correspondência usam R∞ e geram aviso no log.

## 6. Agente 3 — GSF

### O que faz

O Agente 3 calcula descritores do campo espectral a partir da impedância normalizada.

### Cálculos implementados

- Ordenação crescente por frequência para o cálculo.
- Normalização separada das componentes real e imaginária.
- Cálculo de `q = √(xₙ² + yₙ²)`.
- Suavização de `log(q)` por janela móvel configurável.
- Cálculo de α por diferenças sucessivas dividido por `log(φ)`.
- Cálculo do gradiente espectral em relação a `log(f)`.
- `I_crit` como o máximo valor absoluto do gradiente.
- `kφ = q × φ`.

### Classificação operacional

O regime GSF usa a média de α:

- `α > -0,1`: resistivo;
- `-0,5 ≤ α ≤ -0,1`: pseudocapacitivo;
- `-1,0 ≤ α < -0,5`: misto;
- `α < -1,0`: difusivo.

### Visualizações

Gera três SVGs estáticos com backend não interativo do Matplotlib:

- α versus frequência;
- kφ versus frequência;
- gradiente espectral S versus frequência.

### Limitações

Os limiares e a transformação por φ são regras próprias do protocolo e precisam ser validados contra conjuntos de referência. O valor de α usa `log(φ)` no denominador, e não a razão entre frequências adjacentes; essa definição deve permanecer explicitamente documentada para evitar confusão com expoentes obtidos por derivada log-log convencional.

## 7. Agente 4 — ESC

### O que faz

O Agente 4 recebe obrigatoriamente as quatro referências do Agente 2 e calcula, para cada grupo:

```text
Γ = (Z - Z₀) / (Z + Z₀)
```

### Saídas por grupo

- partes real e imaginária de Γ para cada frequência;
- centroide;
- magnitude média;
- ponto de menor frequência;
- indicadores de alta impedância capacitiva e domínio difusivo.

O G2 também recebe interpretação por regras com base em sua posição de baixa frequência.

### Limitações

G2 pode usar uma referência complexa. Nesse caso, a transformação não possui necessariamente todas as propriedades geométricas do coeficiente de reflexão clássico com referência real positiva, e `|Γ|` pode ultrapassar a circunferência unitária desenhada como referência. O código não força os pontos ao disco unitário, o que é matematicamente honesto, mas deve ser considerado na interpretação visual.

## 8. Agente 5 — síntese e relatório

### Síntese determinística

O Agente 5 consolida as métricas dos quatro agentes e aplica regras para:

- verificar concordância entre os regimes DRT e GSF;
- classificar instabilidade espectral pelos limiares de `I_crit`;
- interpretar a faixa de kφ;
- sinalizar possível passivação quando Rct é elevada e o GSF é difusivo;
- incorporar o indicador difusivo do ESC G2.

As regras funcionam sem conexão de rede, chave de API ou modelo local.

### LLM opcional

Quando habilitada, a LLM recebe:

- o contexto de `models/orchestrator_context.txt`;
- as métricas consolidadas;
- o texto produzido pelas regras.

Ela é instruída a produzir um único parágrafo em português, sem diagnóstico clínico ou mecanismo não medido. O resultado da LLM é complementar; as métricas e regras continuam presentes no relatório.

Provedores implementados:

- Ollama local, prioritário no modo `ollama` ou `auto`;
- OpenAI por chave em variável de ambiente, no modo `openai` ou como alternativa em `auto`.

O Ollama é consultado pela API HTTP local. Se permitido na configuração e o executável existir, o Agente 5 pode iniciar `ollama serve`. O modelo configurado é preferido; na ausência dele, o sistema procura outro modelo local compatível e, por fim, usa o primeiro disponível. Falhas podem retornar silenciosamente ao modo de regras, conforme configuração.

### Riscos da LLM

- Não há validação semântica posterior da interpretação além de verificar que o texto não está vazio.
- O texto pode conter uma inferência inadequada mesmo com o prompt restritivo.
- Exceções são capturadas de modo amplo para preservar o fallback, o que favorece disponibilidade, mas pode ocultar a causa operacional se o estado detalhado não for examinado.
- A configuração padrão habilita LLM local; isso aumenta o tempo por amostra e o consumo de RAM. Para lotes extensos, o modo somente regras é mais previsível.

## 9. Relatório HTML

O relatório final é um único arquivo HTML por amostra. Os dados científicos são incorporados como JSON inline e os SVGs do GSF são embutidos no documento.

### Conteúdo

- resumo das métricas principais;
- interpretação determinística;
- interpretação opcional da LLM e estado do provedor;
- Nyquist interativo;
- Nyquist ajustado por Lin-KK e resíduos normalizados por frequência;
- Bode de magnitude e fase;
- espectro DRT e picos;
- mapa q do GSF;
- três gráficos GSF estáticos;
- quatro diagramas ESC.

### Interatividade

- tooltips de frequência nos pontos dos gráficos;
- tooltip dos picos DRT com τ, γ máximo e área integrada;
- zoom e pan no Nyquist;
- zoom e pan nos quatro grupos ESC;
- layout responsivo e visualização incorporada ao painel.

### Segurança e portabilidade

Textos são escapados para HTML, e caracteres sensíveis no JSON inline são neutralizados. Isso reduz o risco de injeção por nomes ou conteúdo textual.

Por padrão, o D3.js é carregado pelo CDN jsDelivr. Com `report_d3_inline=true`, o bundle é baixado uma vez, armazenado atomicamente em `web/static/d3.min.js` e incorporado ao HTML, permitindo relatório totalmente offline. Não existe política CSP definida no documento.

## 10. Execução pela linha de comando

### Execução única

```bash
python run_pipeline.py --input data/input --output output
```

O programa procura recursivamente arquivos EIS `.txt` e `.csv`, processa-os em ordem e encerra. Por padrão, amostras com JSON consolidado existente são ignoradas. `--overwrite` autoriza explicitamente reprocessamento e substituição.

### Monitoramento contínuo

```bash
python run_pipeline.py --input data/input --output output --watch
```

O modo contínuo:

1. processa os arquivos já existentes;
2. inicia um observador recursivo;
3. recebe eventos de criação, alteração e movimentação;
4. aguarda estabilidade de tamanho e data antes de processar;
5. evita duplicação imediata pela assinatura de tamanho e `mtime`.

As assinaturas do observador ficam somente na memória, mas a existência do JSON consolidado impede reprocessamento após reinício sem `--overwrite`. Não há fila durável.

## 11. Painel web local

O painel Flask oferece:

- envio de múltiplos arquivos EIS `.txt` ou `.csv` por seleção ou arraste;
- nomes únicos para uploads repetidos;
- início de execução única;
- início do modo contínuo;
- interrupção do processo;
- acompanhamento de cada agente a partir do log;
- listagem de entradas e relatórios;
- abertura do relatório dentro do painel ou em nova aba;
- endpoint de saúde em `/health`.

O upload é limitado a 256 MB por requisição, usa nomes saneados e grava primeiro com extensão temporária antes da troca para o nome final. Apenas um subprocesso do pipeline é gerenciado por vez.

### Limitações e segurança

- Não existe autenticação, autorização ou proteção CSRF.
- O uso seguro esperado é em `127.0.0.1` ou rede estritamente confiável.
- O Docker publica a porta 8000 e o aplicativo escuta em `0.0.0.0`; regras de firewall são necessárias se o computador estiver em uma rede não confiável.
- O estado é inferido de linhas do log, não de um banco transacional.
- Não há fila de trabalhos, isolamento por usuário nem separação formal entre execuções.
- A lista pode misturar relatórios históricos e atuais, pois não existe identificador de lote.
- O botão de interrupção termina o processo e usa encerramento forçado se necessário; um artefato que estava sendo escrito pode ficar incompleto.

## 12. Configuração

`config/protocol_config.json` concentra:

- nome do protocolo;
- regras de leitura e codificação;
- limiares de qualidade;
- tamanho da grade DRT e proeminência de picos;
- φ e janela de suavização;
- geometria da célula e condutividades cadastradas;
- habilitação e provedor da LLM;
- URL, modelo e limites do Ollama;
- perfis de modelo por memória;
- opção de D3 inline;
- seção explícita de parâmetros reservados.

Sobrescritas por ambiente implementadas:

- `KAIRIS_LLM_ENABLED`;
- `KAIRIS_OLLAMA_URL`;
- `KAIRIS_OLLAMA_MODEL`.

### Parâmetros reservados sem efeito

Os seguintes itens foram movidos para `_reserved_not_yet_implemented`, com aviso explícito de que ainda não produzem efeito:

- `drt_lambda_method`;
- `report_format`;
- `figures_dpi`.

Geometria e condutividade são consumidas no cálculo de Z₀_G4 quando o eletrólito é identificado.

`protocol_schema.json` valida todas as chaves, tipos e faixas antes do processamento e produz mensagens com o caminho exato do erro.

## 13. Instalação e portabilidade

### Assistente

`setup_kairis.py` detecta Windows, Linux e macOS, mede RAM, verifica Python e dependências, reconhece Ollama e recomenda um perfil de modelo.

Perfis atuais:

| RAM detectada | Perfil | Recomendação |
|---|---|---|
| abaixo de 6 GB | 4 GB | `gemma3:1b` |
| 6 a 11,9 GB | 8 GB | modelo quantizado de aproximadamente 4 bilhões de parâmetros |
| 12 GB ou mais | 16 GB+ | modelo quantizado de aproximadamente 4 bilhões de parâmetros |

A instalação do Ollama e o download do modelo são escolhas independentes. O fluxo interativo solicita confirmação; `--yes` representa consentimento explícito antecipado, e `--skip-ollama` evita a oferta.

### Windows

- scripts PowerShell para instalação e inicialização;
- oferta de Python 3.12 pelo `winget` quando ausente;
- ambiente virtual local e instalação por `pip`;
- abertura do navegador por biblioteca Python.

### Linux

- scripts shell para instalação e inicialização;
- reconhecimento de `apt`, `dnf`, `pacman` e `zypper`;
- oferta de instalação de Python e utilitários do ambiente virtual;
- instalador oficial do Ollama somente após confirmação.

### Ressalvas

- A presença do comando Python é verificada antes da criação do ambiente, mas uma versão antiga só é rejeitada posteriormente.
- O fluxo Linux pressupõe `sudo` para instalar pacotes, o que pode exigir adaptação em sistemas mínimos, contêineres ou sessões já executadas como root.
- Se Ollama estiver instalado, mas o serviço estiver parado, a etapa de download do assistente pode exigir que o serviço seja iniciado; o Agente 5 possui sua própria tentativa de inicialização.
- A configuração é alterada no lugar, sem backup automático.
- Os scripts shell não foram executados em um Linux nesta auditoria; sua lógica foi inspecionada, mas a validação real em distribuições suportadas continua necessária.

## 14. Docker

O contêiner usa Python 3.12 slim, instala `libgomp1` e as dependências, cria diretórios de dados, expõe a porta 8000 e inclui um `HEALTHCHECK` HTTP.

Características:

- LLM desabilitada por padrão;
- entradas e saídas persistidas por volumes;
- acesso opcional ao Ollama do hospedeiro por `host.docker.internal`;
- reinício `unless-stopped` no Compose;
- arquivos de ambiente local, entradas, saídas e logs excluídos do contexto de build.

### Pontos de atenção

- A imagem executa como usuário não privilegiado `kairis`.
- `requirements.lock` fixa as versões resolvidas para instalações reproduzíveis.
- A porta publicada expõe um painel sem autenticação.
- O Ollama externo precisa aceitar conexões originadas no contêiner.
- Docker não estava instalado no equipamento auditado; o Dockerfile e o Compose foram inspecionados, mas a imagem não foi construída nem executada nesta auditoria.

## 15. Dependências

Dependências diretamente utilizadas incluem NumPy, SciPy, pandas, Matplotlib, watchdog, Flask e, opcionalmente, o SDK OpenAI.

As dependências diretas sem uso (`impedance`, `fpdf2` e `jinja2`) foram removidas. Jinja permanece apenas como dependência transitiva do Flask no lock. A integração DRT preserva compatibilidade com NumPy 1.x e versões recentes.

## 16. Testes e evidências

### Resultado desta auditoria

```text
25 passed in 10.24s
```

O comando de pré-requisitos também concluiu com dependências OK.

### Cobertura funcional existente

- leitura tabulada com vírgula decimal;
- leitura separada por ponto e vírgula e cabeçalhos com Ω;
- leitura CSV com coluna imaginária assinada `Z''` e preservação de seu sinal;
- sucesso e fallback do orquestrador Ollama com respostas simuladas;
- carregamento de sobrescritas de configuração por ambiente;
- geração de identificadores sem colisão por subpasta;
- perfis de RAM e seleção de modelos instalados;
- cálculo geométrico de Z₀_G4, correspondência de eletrólito e fallback registrado em R∞;
- nomes e nota explícita de Spectral Smoothness no relatório;
- aceitação de um espectro RC ideal pelo Lin-KK e rejeição de entradas com poucos pontos;
- ciclo completo do painel com uma amostra sintética e LLM desabilitada;
- upload, rejeição de extensão e nomes únicos;
- início e parada do monitoramento pelo painel.

O projeto também contém verificações visuais em JavaScript/Playwright para painel e relatório. Elas não fazem parte da execução `pytest` e não foram executadas nesta auditoria.

### Lacunas de teste

- ausência de espectros-padrão com resultados DRT, GSF e ESC numericamente certificados;
- ausência de teste de sensibilidade a ruído, faixa truncada, pontos duplicados e picos sobrepostos;
- ausência de teste de regressão visual incorporado à suíte principal;
- ausência de teste end-to-end real com Ollama;
- ausência de teste real em Linux e macOS;
- ausência de build e teste Docker no ambiente auditado;
- ausência de teste de concorrência, interrupção durante escrita e recuperação de artefato parcial;
- ausência de teste de segurança do painel;
- ausência de medição formal de cobertura de código.

## 17. Achados priorizados

### Prioridade alta

1. **Validação científica insuficiente.** Não há conjunto de referência com valores esperados e tolerâncias para DRT, GSF e ESC. Impacto: mudanças podem alterar resultados sem detecção. Ação: criar fixtures científicos certificados e testes de regressão numérica.
2. **Painel sem controle de acesso.** O serviço permite upload e execução sem autenticação. Impacto: uso indevido se exposto em rede. Ação: manter loopback por padrão, limitar firewall e adicionar autenticação antes de qualquer implantação compartilhada.

### Prioridade média

3. **LLM sem verificador de saída.** A interpretação livre não é validada contra as regras. Ação: restringir a saída a estrutura, validar afirmações e marcar claramente o texto como auxiliar.

### Prioridade baixa

4. **Estado do painel baseado em log.** Ação: registrar execução e progresso em manifesto estruturado.
5. **Histórico detalhado do watch apenas em memória.** Ação: persistir assinaturas quando for necessário distinguir alteração de arquivo de mera existência de resultado.

## 18. Pontos positivos de engenharia

- Separação clara entre agentes e motores científicos.
- Cada agente pode ser executado como arquivo Python independente.
- O Agente 4 recebe as referências do Agente 2, preservando o encadeamento pretendido.
- Falha de uma amostra não encerra o lote inteiro.
- Nomes homônimos em subpastas não colidem.
- O modo sem LLM é funcional e preservado como fallback.
- Instalações e downloads opcionais exigem decisão explícita.
- Leitor EIS tolera formatos reais heterogêneos sem depender de um único cabeçalho.
- Relatório combina dados inline, SVGs científicos e gráficos interativos.
- Serialização trata tipos NumPy e valores não finitos.
- Upload usa saneamento de nome e troca após gravação temporária.
- Scripts e código evitam caminhos rígidos específicos de Windows para a operação normal.
- Há teste de integração real do pipeline por meio do painel Flask.

## 19. Recomendações de evolução

Ordem sugerida:

1. Separar o limiar de resíduo permissivo da fração máxima usada por `spectral_smooth`.
2. Criar um pequeno conjunto de espectros de referência, incluindo sintéticos e experimentais, com resultados e tolerâncias aprovados por pesquisadores.
3. Adicionar ID de lote à proveniência atual para agrupar execuções.
4. Restringir o painel a loopback por padrão no Compose ou implementar autenticação para uso em rede.
5. Executar uma matriz de integração em Windows e Linux e construir a imagem Docker automaticamente.
6. Incorporar testes Playwright à rotina de validação.

## 20. Critério de uso responsável

O KAIRIS deve ser tratado, no estado auditado, como uma plataforma de análise e apoio interpretativo. As métricas devem ser confrontadas com a qualidade do experimento, faixa de frequência, geometria da célula, repetibilidade, controles e conhecimento eletroquímico do pesquisador. Alertas produzidos por regras ou LLM não constituem, isoladamente, identificação causal de mecanismo. Para publicação, decisão regulatória ou comparação quantitativa entre laboratórios, recomenda-se completar as validações numéricas, metrológicas e de reprodutibilidade indicadas nesta auditoria.
