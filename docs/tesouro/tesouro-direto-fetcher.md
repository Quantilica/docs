---
title: tesouro-direto-fetcher — Microdados do Tesouro Direto
description: Download e visualização de dados históricos do programa Tesouro Direto (preços, estoque, investidores, operações). Altair e CKAN integrados.
---

# Tesouro Direto

**tesouro-direto-fetcher** simplifica o download, normalização e plotagem nativa da massa de microdados gerados pelo programa de títulos públicos do Brasil, extraídos via API CKAN oficial (Tesouro Transparente).

!!! warning "Pegadinhas da fonte oficial"

    - **Nomenclaturas Vivas via CKAN.** O CKAN governamental embute um *timestamp* dinâmico nos IDs de download. A CLI resolve isso automaticamente nomeando os arquivos para `taxas-...@20251230T102010.csv`. Nunca utilize caminhos de arquivo fixos no seu código; use resoluções `glob`.
    - **CSVs Crípticos Brasileiros.** Datas vêm nativamente no formato dia-mês-ano (pt-BR) e frações monetárias vêm com vírgula (`,`) ao invés de ponto decimal. Se importar em Pandas diretamente você vai corromper a base. Use as ferramentas de conversão nativas da Quantilica.
    - **Download em threads, sem `asyncio`.** O pacote não usa `asyncio`: o download é síncrono e paraleliza com threads (`--workers`), então não há conflito de event loop em Jupyter.

## Instalação

```shell
# Via CLI unificada (recomendado)
quantilica install tesouro-direto

# Com o extra de análise, para os comandos convert e pipeline da CLI
quantilica install tesouro-direto --extra analysis

# Ou como biblioteca no seu projeto
uv add "tesouro-direto-fetcher[analysis]" --index https://index.quantilica.com/simple/
```

*Nota: O extra `[analysis]` carrega o Polars e o Altair para habilitar visualizações. Omiti-lo instalará apenas os motores básicos de rede.*

## CLI Oficial (Ambiente Unificado)

Use o executor unificado da Quantilica para contornar a API CKAN e extrair/converter as vastas bases:

```bash
# Inspecionar (dry-run) o grupo de preços sem escrever no disco
quantilica td sync taxas-dos-titulos-ofertados-pelo-tesouro-direto --dry-run -o ./data

# Baixar a base de investidores e converter os CSVs para Parquet
# (a conversão exige o extra de análise)
quantilica td sync investidores-do-tesouro-direto -o ./data
quantilica td convert ./data

# Baixar o universo inteiro (todos os grupos)
quantilica td sync -o ./data
```

---

## Datasets Disponíveis (Macro-Grupos)

Os grupos (argumentos posicionais de `quantilica td sync`) correspondem aos recursos do Tesouro Transparente:

- **Preços e taxas** (`taxas-dos-titulos-ofertados-pelo-tesouro-direto`)
- **Estoque** (`estoque-do-tesouro-direto`)
- **Investidores** (`investidores-do-tesouro-direto`)
- **Operações** (`operacoes-do-tesouro-direto`)
- **Resgates** (`resgates-do-tesouro-direto`, inclui recompras) e **Vendas** (`vendas-do-tesouro-direto`)

## Cookbook Analítico: Plotando a Série de Taxas

O `tesouro-direto-fetcher` carrega baterias inclusas. Ele já traz o Polars para leitura limpa (consertando as virgulas decimais do governo) e o **Altair** para gráficos de qualidade acadêmica:

```python
import polars as pl
from pathlib import Path
from tesouro_direto_fetcher import reader, plot
from tesouro_direto_fetcher.constants import Column

# 1. Carrega os preços (já corrigindo formatos de data pt-BR sob os panos)
caminho_csv = list(Path("./data").rglob("taxas-dos-titulos*.csv"))[0]
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

## Binário `tesouro-direto-fetcher`

O pacote também instala o comando `tesouro-direto-fetcher`, equivalente a `quantilica td`. Ele não dispensa o host: depende do `quantilica-cli` e, sem ele, imprime `Instale via "quantilica install td"` e sai com código 1. Para baixar sem visualização, em scripts ou cron:

```bash
tesouro-direto-fetcher sync -o ./data
tesouro-direto-fetcher convert ./data
tesouro-direto-fetcher sync taxas-dos-titulos-ofertados-pelo-tesouro-direto -o ./data --workers 4
```

## Saiba Mais

- **[Cálculo de Retornos de Renda Fixa](../concepts/calculo-retornos-renda-fixa.md)** — A matemática por trás de YTM, duration e retorno real
- **[Arquitetura do Ecossistema](../concepts/arquitetura.md)** — Design do sistema
- **[Tesouro Transparente](https://www.tesourotransparente.gov.br/)** — Fonte oficial CKAN
