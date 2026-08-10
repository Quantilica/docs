---
title: tesouro-direto-fetcher — Microdados do Tesouro Direto
description: Download e visualização de dados históricos do programa Tesouro Direto (preços, estoque, investidores, operações). Altair e CKAN integrados.
---

# Tesouro Direto

**tesouro-direto-fetcher** simplifica o download, normalização e plotagem nativa da massa de microdados gerados pelo programa de títulos públicos do Brasil, extraídos via API CKAN oficial (Tesouro Transparente).

!!! warning "Pegadinhas da fonte oficial"

    - **Nomenclaturas Vivas via CKAN.** O CKAN governamental embute um *timestamp* dinâmico nos IDs de download. A CLI resolve isso automaticamente nomeando os arquivos para `taxas-...@20251230T102010.csv`. Nunca utilize caminhos de arquivo fixos no seu código; use resoluções `glob`.
    - **CSVs Crípticos Brasileiros.** Datas vêm nativamente no formato dia-mês-ano (pt-BR) e frações monetárias vêm com vírgula (`,`) ao invés de ponto decimal. Se importar em Pandas diretamente você vai corromper a base. Use as ferramentas de conversão nativas da Quantilica.
    - **Loop Eventuais Assíncronos.** O core de extração roda via `asyncio`. Se você tentar baixar dados diretamente no escopo de um Jupyter Notebook que já tenha o próprio `loop`, acontecerá conflito. Use o `nest_asyncio` no Jupyter ou acesse os dados indiretamente via CLI.

## Instalação

```shell
pip install "tesouro-direto-fetcher[analysis]"
```

*Nota: O extra `[analysis]` carrega o Polars e o Altair para habilitar visualizações. Omiti-lo instalará apenas os motores básicos de rede.*

## CLI Oficial (Ambiente Unificado)

Use o executor unificado da Quantilica para contornar a API CKAN e extrair/converter as vastas bases:

```bash
# Inspecionar (dry-run) os datasets de preços sem escrever no disco
quantilica td sync --dataset prices --dry-run -o ./data

# Pipeline completo: baixar a base de investidores e já convertê-la para 
# arquivos Parquet limpos e serializados
quantilica td pipeline --dataset investors -o ./data

# Baixar o universo inteiro (Estoque, Operações, Preços, Investidores, Vendas)
quantilica td sync -o ./data
```

---

## Datasets Disponíveis (Macro-Grupos)

Os parâmetros `--dataset` mapeiam diretamente para chaves CKAN de infraestrutura gigantesca:

- **`prices`** (`taxas-dos-titulos-ofertados-pelo-tesouro-direto`)
- **`stock`** (`estoque-do-tesouro-direto`)
- **`investors`** (`investidores-do-tesouro-direto`)
- **`operations`** (`operacoes-do-tesouro-direto`)
- **`buybacks`** / **`sales`** (recompras e emissões diretas)

## Cookbook Analítico: Plotando a Série de Taxas 

O `tesouro-direto-fetcher` carrega baterias inclusas. Ele já traz o Polars para leitura limpa (consertando as virgulas decimais do governo) e o **Altair** para gráficos de qualidade acadêmica:

```python
import polars as pl
from pathlib import Path
from tesouro_direto_fetcher import reader, plot
from tesouro_direto_fetcher.constants import Column

# 1. Carrega os preços (já corrigindo formatos de data pt-BR sob os panos)
caminho_csv = list(Path("./data").glob("taxas-dos-titulos*.csv"))[0]
df_prices = reader.read_prices(caminho_csv)

# 2. Utiliza o módulo plot nativo do fetcher para exibir o 
# Histórico de Preços Base do Tesouro Selic
grafico = plot.plot_prices(
    df_prices,
    bond_type="Tesouro Selic",
    variable=Column.BASE_PRICE.value,
)

# Renderiza no browser ou jupyter notebook
grafico.display()

# Opcional: exporta em HTML interativo
grafico.save("historico_tesouro_selic.html")
```

Para analisar demografias massivas, a biblioteca dispõe de gráficos populacionais automáticos:

```python
# Lê investidores
df_investors = reader.read_investors(caminho_investidores_csv)

# Rende pirâmide populacional (idade vs gênero) do Brasil rentista
plot.plot_investors_population_pyramid(df_investors).display()
```

## Uso Isolado (Sem Ambiente Unificado)

```bash
tesouro-direto-fetcher pipeline -o ./data
tesouro-direto-fetcher sync --dataset prices -o ./data
```

E para downloads assíncronos diretamente em scripts backend (sem visualização):

```python
import asyncio
from pathlib import Path
from tesouro_direto_fetcher import downloader

asyncio.run(
    downloader.download(
        dest_dir=Path("./data"),
        dataset_id="taxas-dos-titulos-ofertados-pelo-tesouro-direto",
        max_concurrency=4,
    )
)
```

## Saiba Mais

- **[Cálculo de Retornos de Renda Fixa](../concepts/calculo-retornos-renda-fixa.md)** — A matemática por trás de YTM, duration e retorno real
- **[Arquitetura do Ecossistema](../concepts/arquitetura.md)** — Design do sistema
- **[Tesouro Transparente](https://www.tesourotransparente.gov.br/)** — Fonte oficial CKAN
