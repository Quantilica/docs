---
title: inmet-fetcher — Dados meteorológicos do BDMEP/INMET
description: Baixa o BDMEP em paralelo, trata encoding latin-1, descarta o bloco de metadados do cabeçalho e exporta Parquet com colunas em snake_case e datetime nativo.
---

# Clima e Ambiente (INMET)

Dados meteorológicos e ambientais brasileiros oficiais do INMET (Instituto Nacional de Meteorologia).

O **inmet-fetcher** domina a rede nacional de dados meteorológicos históricos do Brasil (BDMEP). A extração abrange precipitação, ventos, radiação e temperaturas, pavimentando análises agrícolas, climáticas e energéticas.

!!! warning "Pegadinhas da fonte oficial"

    - **Encoding caótico (`latin-1`).** Os ZIPs anuais vêm comprimidos e codificados em latin-1 O módulo de leitura decodifica em latin-1; não há tratamento explícito de *Byte Order Mark*.
    - **Cabeçalho com metadados.** Cada arquivo traz um bloco de metadados da estação (região, UF, código WMO, latitude, longitude, altitude e data de fundação) antes da tabela. O leitor descarta 8 linhas fixas (`skip_rows=8`) antes do cabeçalho tabular; um arquivo com outro número de linhas de metadados não é tratado.
    - **A praga do `-9999`.** O INMET usa `-9999` magicamente no lugar de NULL para indicar ausência de leitura do sensor. **Perigo:** se não filtrado, a média da sua temperatura cairá para graus negativos absolutos. A biblioteca conserta isso mapeando para o `null` do Polars na leitura.
    - **Time Series Separadas.** As colunas `data` e `hora` vêm cindidas e formatadas irregularmente. O código combina ambas num `datetime` nativo contínuo, salvando você de manipulações tediosas.
    - **Gap de Automação.** Há um abismo tecnológico: estacões convencionais (leitura humana rara) e estacões automáticas (códigos WMO `A###` com leituras horárias contínuas). Não interpole ambas as naturezas sem reamostragem cuidadosa.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install inmet

# Ou como biblioteca no seu projeto
uv add inmet-fetcher --index https://index.quantilica.com/simple/
```

**Requisitos:** Python 3.12+

## CLI Oficial (Ambiente Unificado)

Use o executor central unificado para extrair os lotes climáticos gigantescos. O comando sincroniza paralelamente os zips do governo:

```bash
# Baixa o grupo bdmep (dados das estações meteorológicas)
quantilica inmet sync bdmep -o ./data

# Todos os grupos, com paralelismo intenso (8 workers)
quantilica inmet sync -o ./data --workers 8
```

---

## Cookbook Analítico: Meteorologia Escalonável

O banco do INMET cresceu enormemente após 2008 devido ao auge das estações automáticas. Quando descompactado, os CSVs são de leitura dolorosa. O ecossistema Quantilica disponibiliza a conversão forte e tipada para `Parquet` obedecendo contratos exatos de schemas (`BDMEP_CONTRACT`).

Para ler o diretório de dados massivos e visualizar anomalias térmicas, use o `Polars`:

```python
import polars as pl
from pathlib import Path
import inmet_fetcher as inmet

# 1. Supondo que você sincronizou os arquivos brutos com a CLI
data_dir = Path("./data")

# 2. Use a API de extração da Quantilica para normalizar
# todos os CSVs bizarros em DataFrames em memória
df_inmet = inmet.read(
    data_dir,
    years=[2022, 2023],
    uf=["SP", "RJ", "MG"]
)

# 3. Descobrindo o pico de temperatura máxima (Verão extremo)
# O -9999 já foi expurgado, então a métrica agg.max() é segura
calor_historico = (
    df_inmet
    .with_columns(
        pl.col("data_hora").dt.date().alias("dia_registro")
    )
    .group_by(["uf", "dia_registro"])
    .agg(pl.col("temperatura_maxima").max().alias("pico_termico"))
    .sort("pico_termico", descending=True)
)

print(calor_historico.head(5))
```

### Salvando em Parquet (Limpeza Permanente)

Em vez de reler CSVs, grave seu resultado permanentemente utilizando as classes do core da Quantilica, garantindo rastreabilidade no cabeçalho (*manifest*):

```python
from quantilica.core.manifests import DownloadManifest

manifest = DownloadManifest.from_file(
    source_id="inmet",
    dataset_id="bdmep",
    url="https://portal.inmet.gov.br/uploads/dadoshistoricos/2023.zip",
    file_path="./data/bdmep/2023/inmet-bdmep_2023@20240101.zip",
    producer="inmet-fetcher"
)

inmet.write_to_parquet(df_inmet, "output/clima_sudeste_2023.parquet", manifest=manifest)
```

## Dicionário de Variáveis (Macro-Colunas)

O catálogo impõe e padroniza as 17 medições abaixo em todos os arquivos de saída:

- `precipitacao` (mm)
- `pressao_atmosferica` (mB), `pressao_atmosferica_maxima` / `_minima`
- `radiacao` (kJ/m²)
- `temperatura_ar` (°C), `temperatura_maxima` / `_minima`
- `temperatura_orvalho` (°C), `temperatura_orvalho_maxima` / `_minima`
- `umidade_relativa` (%), `umidade_relativa_maxima` / `_minima`
- `vento_velocidade` (m/s), `vento_rajada`, `vento_direcao`

Metadados automáticos também apensados na leitura: `regiao`, `uf`, `codigo_wmo`, `latitude`, `longitude`, `altitude`.

## Binário `inmet-fetcher`

O pacote também instala o comando `inmet-fetcher`, equivalente a `quantilica inmet`. Ele não dispensa o host: depende do `quantilica-cli` e, sem ele, imprime `Instale via "quantilica install inmet"` e sai com código 1.

```bash
inmet-fetcher sync bdmep -o ./data
```

## Saiba Mais
- **[Arquitetura do Ecossistema](../concepts/arquitetura.md)** — Design do sistema
