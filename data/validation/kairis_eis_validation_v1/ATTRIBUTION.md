# Atribuição dos dados experimentais públicos

**Título:** EIS data of 54 21700 cells  
**Autores:** Manuel Moertelmaier, Manuel Kasper e Simon Clark  
**Versão:** 1.0.0, publicada em 26 de maio de 2025  
**DOI:** https://doi.org/10.5281/zenodo.15422339  
**Licença:** Creative Commons Attribution 4.0 International (CC BY 4.0)  
**Fonte:** https://zenodo.org/records/15422339

Os 54 arquivos `ID01.csv` a `ID54.csv` foram baixados pela API oficial do
Zenodo. O construtor verifica a licença informada pela API, a contagem esperada e
o MD5 publicado para cada arquivo. O manifesto KAIRIS acrescenta SHA-256 sem
alterar os CSV originais.

Escopo declarado pelos autores: EIS galvanostática em 54 células cilíndricas
NMC811 formato 21700, a 30% de estado de carga, medida com sistema Keysight
SL1007A Scienlab. O corpus KAIRIS não atribui eletrólito, mecanismo ou circuito
equivalente que a fonte não declarou.

## AutoECM/BatteryDEV

**Artigo:** *Machine Learning Benchmarks for the Classification of Equivalent
Circuit Models from Electrochemical Impedance Spectra*  
**Autores:** Joachim Schaeffer et al.  
**DOI:** https://doi.org/10.1149/1945-7111/acd8fb  
**Repositório:** https://github.com/BatteryDEV/AutoECM  
**Licença dos dados:** CC BY 4.0

Os arquivos originais `train_data.csv` e `test_data.csv` contêm espectros
sintéticos rotulados. Para manter o corpus operacional compacto, o KAIRIS converte
deterministicamente os cinco primeiros espectros de treino e os três primeiros de
teste de cada uma das nove classes: 45 exemplos de treino e 27 de holdout. Os CSV
originais e a licença publicada permanecem ao lado das conversões; hashes e regra
de seleção constam em `public/autoecm_ccby4/source_metadata.json`.

