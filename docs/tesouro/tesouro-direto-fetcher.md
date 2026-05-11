---
title: tesouro-direto-fetcher — Tesouro Direto em Python
description: Download, leitura e visualização de dados históricos do Tesouro Direto via API CKAN (Tesouro Transparente). Leitores especializados por dataset e gráficos prontos com Altair.
---

# tesouro-direto-fetcher — Baixar, Analisar e Plotar Dados do Tesouro Direto Brasileiro

**tesouro-direto-fetcher** é um pacote Python que simplifica o download, a leitura e a visualização de dados históricos do programa Tesouro Direto brasileiro. Alavanca a API CKAN oficial (Tesouro Transparente) para buscar os datasets mais atualizados.

!!! warning "Pegadinhas da fonte oficial"

    - **Nome de arquivo carrega timestamp.** Cada download fica como `taxas-...@20251230T102010.csv`. Não tente um nome estável — passe um diretório de destino e use `glob` para encontrar o mais recente.
    - **Um dataset, vários CSVs.** Preços, estoque, investidores, operações são datasets CKAN separados. Use o `reader.read_prices`, `read_stock`, `read_investors` — não tente um único parser genérico.
    - **Datas vêm em pt-BR.** `dd/mm/aaaa` com decimal `,`. Os leitores já tratam isso; se você ler com `pl.read_csv` cru, vai apanhar.
    - **Licença GPL-3.0.** Este é o único pacote da Quantilica que não é MIT. Se você for embarcar em produto fechado, atente.
    - **`asyncio.run` reinicia event loop.** Em Jupyter, prefira `await downloader.download(...)` direto na célula com `nest_asyncio` ou use o CLI.

## Recursos

- **Downloads Automatizados**: Busque datasets diretamente da API CKAN do Governo
- **Leitores Especializados**: Funções dedicadas para ler e fazer parse de CSVs para Preços, Estoque, Investidores, Operações, Vendas, Recompras/Resgate, e mais
- **Dados Padronizados**: Todos os DataFrames vêm com nomes de coluna consistentes e amigáveis para analistas, definidos em um esquema robusto
- **Visualização**: Módulo de plotagem integrado que retorna gráficos **Altair** para análise de séries temporais, distribuição e demografia (nenhum Matplotlib/Seaborn necessário)
- **CLI**: Uma interface de linha de comando conveniente para busca rápida de dados

## Instalação

Este pacote está disponível via GitHub. Você pode instalá-lo usando `pip`:

**Apenas download (dependências mínimas):**

```shell
pip install "git+https://github.com/Quantilica/tesouro-direto-fetcher#egg=tesouro-direto-fetcher"
```

**Instalação completa com recursos de leitura, análise e plotagem:**

```shell
pip install "git+https://github.com/Quantilica/tesouro-direto-fetcher#egg=tesouro-direto-fetcher[analysis]"
```

A instalação mínima inclui apenas `httpx` e `tqdm` para download de dados. Os extras `[analysis]` adicionam `polars` (parsing CSV, analytics) e `altair[save]` (gráficos).

## Uso

### O `tesouro-direto-fetcher` CLI

O pacote instala um comando `tesouro-direto-fetcher` com três subcomandos:

```text
tesouro-direto-fetcher <command> [options]

Comandos:
  download [-o OUTPUT_DIR] [--dataset DATASET]
        Baixar um dataset CKAN. DATASET ∈ {prices, operations, investors,
        stock, buybacks, sales, all}. Padrão: prices.
  info     [-o OUTPUT_DIR] [--dataset DATASET]
        Imprimir recursos, tamanhos, Last-Modified, e se cada arquivo seria
        baixado — sem escrever nada.
  convert  FILE [--type {prices,operations,investors,stock,buybacks,sales,maturities,infer}]
        Converter um CSV baixado para Parquet. `--type infer` (padrão) detecta
        o dataset do nome do arquivo. Requer os extras `analysis`.
```

`OUTPUT_DIR` padrão é `data`.

```bash
# Inspecionar, baixar, converter
tesouro-direto-fetcher info     --dataset prices -o ./data
tesouro-direto-fetcher download --dataset prices -o ./data
tesouro-direto-fetcher convert  ./data/taxas-dos-titulos-ofertados-pelo-tesouro-direto@*.csv

# Baixar cada dataset
tesouro-direto-fetcher download --dataset all -o ./data
```

### O `tesouro-direto-fetcher` Pacote Python

Você pode usar `tesouro-direto-fetcher` como uma biblioteca em seus scripts Python ou Notebooks Jupyter.

#### Baixando Dados

`downloader.download` é assíncrono; envolva com `asyncio.run` ou `await` dentro de uma coroutine.

```python
import asyncio
from pathlib import Path
from tesouro_direto_fetcher import downloader

asyncio.run(
    downloader.download(
        dest_dir=Path("./data"),
        dataset_id="taxas-dos-titulos-ofertados-pelo-tesouro-direto",
        max_concurrency=3,
    )
)

# Inspecionar o que seria baixado sem escrever nada
infos = asyncio.run(
    downloader.get_download_info(
        dest_dir=Path("./data"),
        dataset_id="taxas-dos-titulos-ofertados-pelo-tesouro-direto",
    )
)
```

#### Lendo Dados

O módulo `tesouro_direto_fetcher.reader` fornece funções especializadas para cada tipo de dataset.

```python
from pathlib import Path
from tesouro_direto_fetcher import reader

# Ler Preços/Taxas
df_prices = reader.read_prices(
    Path(
        ".", "data",
        "taxas-dos-titulos-ofertados-pelo-tesouro-direto@20251230T102010.csv"
    )
)

# Ler Estoque
df_stock = reader.read_stock(
    Path(
        ".", "data",
        "estoque-do-tesouro-direto@20251201T102018.csv"
    )
)

# Ler Investidores
df_investors = reader.read_investors(
    Path(
        ".", "data",
        "investidores-do-tesouro-direto-de-2024@20251205T131939.csv"
    )
)
```

#### Plotagem de Dados

Módulo `tesouro_direto_fetcher.plot` retorna gráficos Altair (`alt.Chart`). Exiba-os em um notebook com `chart.display()` ou salve com `chart.save("nome.png")` / `.html` / `.svg`.

```python
from tesouro_direto_fetcher import plot
from tesouro_direto_fetcher.constants import Column

# 1. Plotar Histórico de Preços
plot.plot_prices(
    df_prices,
    bond_type="Tesouro Selic",
    variable=Column.BASE_PRICE.value,
).save("prices_tesouro-selic.html")

# 2. Plotar Evolução de Estoque por Tipo de Título
plot.plot_stock(df_stock, by_bond_type=True).save("stock_evolution_by_type.html")

# 3. Plotar Demografia de Investidores (Pirâmide Populacional)
plot.plot_investors_population_pyramid(df_investors).save("investors_pyramid.html")

# 4. Plotar Demografia de Investidores (ex. gráfico de barras de Profissão)
plot.plot_investors_demographics(
    df_investors,
    column=Column.PROFESSION.value,
).save("investors_profession.html")
```

Outros helpers de plotagem expostos por `tesouro_direto_fetcher.plot`: `plot_investors_evolution`, `plot_operations`, `plot_sales`, `plot_buybacks`, `plot_maturities`, `plot_interest_coupons`.

## Fonte de Dados

Todos os dados são buscados do oficial **Tesouro Transparente** através de sua [API CKAN](https://www.tesourotransparente.gov.br/ckan/).

- **Preços**: `taxas-dos-titulos-ofertados-pelo-tesouro-direto`
- **Estoque**: `estoque-do-tesouro-direto`
- **Investidores**: `investidores-do-tesouro-direto`
- **Operações**: `operacoes-do-tesouro-direto`
- **Vendas**: `vendas-do-tesouro-direto`
- **Recompras**: `recompras-do-tesouro-direto`

## Saiba Mais

- **[Visão Geral do Tesouro Direto](index.md)** — Todas as ferramentas do Tesouro Direto
- **[Guia de Retornos de Portfólio](calculo-retornos.md)** — Como calcular retornos de títulos
- **[Arquitetura da Plataforma](../concepts/arquitetura.md)** — Design do sistema
- **[Tesouro Transparente](https://www.tesourotransparente.gov.br/)** — Fonte de dados oficial
