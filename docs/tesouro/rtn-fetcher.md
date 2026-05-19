---
title: rtn-fetcher — Resultado do Tesouro Nacional em Python
description: Baixa, lê e normaliza a planilha Excel do RTN (24+ abas, células mescladas, hierarquia implícita) em tabela longa com expansão de contas pronta para análise.
---

# rtn-fetcher — Resultado do Tesouro Nacional (RTN) Brasileiro

**rtn-fetcher** é um pacote Python que baixa, extrai e normaliza o *Resultado do Tesouro Nacional* (RTN) — relatório mensal de resultados fiscais federais do Brasil. Transforma as pastas de trabalho Excel com múltiplas abas do Tesouro em tabelas de formato longo limpo com expansão hierárquica de contas, prontas para análise ou carregamento em warehouse.

!!! warning "Pegadinhas da fonte oficial"

    - **Headers não estão em linha fixa.** Cada uma das 24+ abas tem cabeçalho em linhas diferentes, frequentemente com células mescladas. O leitor detecta dinamicamente; não tente `header=0`.
    - **Hierarquia de contas é implícita.** Código `1.2.3` exige a existência de `1` e `1.2` — o `rtn-fetcher` expande em uma tabela de dimensão separada.
    - **Unidades mudam por aba.** Abas `1.x` em milhões de R$; abas `2.x-A` em fração do PIB; aba `1.2-B` deflacionada por IPCA. Confira `unit` antes de somar.
    - **Períodos misturados.** Mensal, trimestral, anual — em colunas diferentes na mesma planilha. O leitor separa em `year`/`month` ou `year`/`quarter`.
    - **Abas 3.1 e 3.2 não são suportadas.** Layout comparativo com headers multi-nível — ainda não normalizado.

## O Que É

O *Resultado do Tesouro Nacional* contém dados fiscais consolidados do Governo Federal Brasileiro: receitas, despesas e resultado primário, em valores correntes e constantes, mensais, trimestrais e anuais, também como percentuais do PIB. O Tesouro publica isso como uma extensa pasta de trabalho Excel com 24+ abas, cada uma com seu próprio layout de header e hierarquia de contas. `rtn-fetcher` automatiza o pipeline de fetch-and-normalize para você ir da URL oficial a uma tabela de formato longo arrumada em poucas linhas de Python — ou um comando CLI.

**Source:** [Tesouro Nacional — RTN](https://www.gov.br/tesouronacional/pt-br/estatisticas-fiscais-e-planejamento/resultado-do-tesouro-nacional-rtn)

## O Desafio

- **Excel com múltiplas abas** com headers variáveis e células mescladas em 24 abas suportadas — linhas de header não estão em posições fixas, requerendo detecção dinâmica.
- **Hierarquia de contas em formato amplo**: códigos como `1.2.3` carregam níveis pai implícitos (`1`, `1.2`) que precisam ser expandidos em uma tabela de dimensão separada.
- **Unidades e períodos mistos**: valores aparecem como milhões de R$, R$ constantes, ou % do PIB; períodos misturam mensal, trimestral e anual — cada aba precisa da normalização correta.

## Recursos

- Download automático da pasta de trabalho RTN mais recente com deduplicação baseada em timestamp
- Lê 24 abas suportadas cobrindo mensal / trimestral / anual; corrente / constante; % do PIB
- Saída em formato longo com expansão hierárquica de contas
- Normalização de unidades (milhões de R$ → reais; % do PIB preservado como fração)
- Período dividido em colunas `year` / `month` ou `year` / `quarter`
- Hierarquia de contas retornada como tabela de dimensão separada
- CLI com `sync` (todas as publicações; `--latest` para a série histórica), `export` (Excel/SQLite) e `pipeline` (sync → export)

## Abas Suportadas

| Abas | Descrição | Período | Unidade |
|--------|-------------|--------|------|
| 1.1, 1.2, 1.3, 1.4, 1.5, 1.6 | Série mensal, valores correntes | Mensal | R$ |
| 1.1-A, 1.2-A, 1.3-A, 1.4-A, 1.5-A | Série mensal, valores constantes | Mensal | R$ |
| 1.2-B | Série mensal, rolling 12-meses, deflacionado pelo IPCA | Mensal | R$ |
| 2.1, 2.2, 2.3, 2.4, 2.5 | Série anual, valores correntes | Anual | R$ |
| 2.1-A, 2.2-A, 2.3-A, 2.4-A, 2.5-A | Série anual, % do PIB | Anual | Fração do PIB |
| 4.1, 4.2 | Série trimestral, Orçamento do Governo Central | Trimestral | R$ |

As abas `3.1` e `3.2` usam um layout comparativo de publicação atual com headers multi-nível e ainda não são normalizadas pelo leitor de série histórica.

## Instalação

Requer Python 3.12+.

```bash
pip install git+https://github.com/Quantilica/rtn-fetcher.git
# ou
uv add "git+https://github.com/Quantilica/rtn-fetcher.git"
```

Dependências: `httpx`, `openpyxl`, `beautifulsoup4`.

## Interface de Linha de Comando

O pacote instala um comando `rtn-fetcher` com os subcomandos `sync`, `export` e `pipeline`:

```bash
rtn-fetcher --help
rtn-fetcher --version

# Sincronizar todas as publicações RTN
rtn-fetcher sync

# Baixar apenas o arquivo da série histórica mais recente
rtn-fetcher sync --latest

# Exportar dados para outros formatos
rtn-fetcher export excel
rtn-fetcher export sqlite

# Pipeline completo (sync → export)
rtn-fetcher pipeline --format excel
```

### `sync` — sincronização completa

Busca metadados da página de publicações do Tesouro Nacional, identifica todos os links de download e baixa os arquivos ainda ausentes no diretório local. Os metadados HTML são cacheados em `<output>/metadata.html`; na próxima execução o cache é reutilizado automaticamente.

```bash
rtn-fetcher sync -o /data/rtn              # Diretório de destino (padrão: /data/rtn)
rtn-fetcher sync --force                   # Refaz o fetch de metadados mesmo se já existe
rtn-fetcher sync --concurrency 8           # Até 8 downloads simultâneos (padrão: 4)
rtn-fetcher sync --dry-run                 # Lista os arquivos sem baixar
rtn-fetcher sync --metadata metadata.json  # Usa JSON de metadados existente (offline)
rtn-fetcher sync --latest                  # Apenas a série histórica mais recente
rtn-fetcher --verbose sync                 # Exibe logs detalhados
```

### `export` — exportação

Ambos os subcomandos baixam automaticamente a pasta de trabalho mais recente se nenhum `--file` for fornecido, e escrevem todas as abas suportadas junto com a dimensão de hierarquia de contas.

```bash
rtn-fetcher export excel --save-as rtn_data.xlsx
rtn-fetcher export sqlite --save-as rtn_data.db

# Usar arquivo local já baixado (sem nova requisição de rede)
rtn-fetcher export excel  --file rtn@20250101T120000.xlsx --save-as rtn_data.xlsx
rtn-fetcher export sqlite --file rtn@20250101T120000.xlsx --save-as rtn_data.db

# Sobrescrever banco SQLite existente sem confirmação
rtn-fetcher export sqlite --save-as rtn_data.db --force
```

### Via `quantilica-cli`

Quando instalado no mesmo ambiente que `quantilica-cli`, o rtn-fetcher é descoberto automaticamente via entry point:

```bash
quantilica fetch rtn sync
quantilica fetch rtn sync --latest
quantilica fetch rtn export excel
quantilica fetch rtn export sqlite
quantilica fetch rtn pipeline --format sqlite
```

## API Python

### Baixar

```python
from pathlib import Path
from rtn_fetcher import download_latest_file

filepath = download_latest_file(Path("data"))
print(f"Baixado: {filepath}")
```

`download_latest_file` retorna o `Path` do arquivo baixado, ou `None` se uma cópia atual já existe no destino.

### Ler uma aba única

```python
from pathlib import Path
from rtn_fetcher import read_sheet, write_table_to_csv

filepath = Path("data/rtn_202412301200.xlsx")
data, accounts = read_sheet(filepath, "1.2")

print(f"Dados:     {data.nrows} linhas x {data.ncols} colunas")
print(f"Contas:    {accounts.nrows} linhas x {accounts.ncols} colunas")

write_table_to_csv(data,     Path("output/rtn_1_2_data.csv"))
write_table_to_csv(accounts, Path("output/rtn_1_2_accounts.csv"))
```

`read_sheet(filepath, sheet_name)` retorna uma tupla `(data, accounts)` de instâncias `Tbl` — a tabela de fatos em formato longo e a dimensão de hierarquia de contas.

### Gravar Parquet com proveniência

Para saída tipada e com manifesto embutido no header, use `write_table_to_parquet`. Ele aplica o `DataContract` da planilha (via `build_contract`) e escreve via `quantilica-io`:

```python
from pathlib import Path
from quantilica_core.manifests import DownloadManifest
from rtn_fetcher import read_sheet, write_table_to_parquet

filepath = Path("data/rtn_202412301200.xlsx")
data, _ = read_sheet(filepath, "2.1")

manifest = DownloadManifest.from_file(
    source_id="tesouro-nacional",
    dataset_id="rtn",
    url="http://sisweb.tesouro.gov.br/apex/cosis/thot/link/rtn/serie-historica",
    file_path=filepath,
    producer="rtn-fetcher",
)
write_table_to_parquet(data, Path("output/rtn_2_1.parquet"), "2.1",
                      manifest=manifest)
```

O contrato é derivado de `SHEET_CONFIGS[sheet]`: `year` para anuais, `year/month` para mensais, `year/quarter` para trimestrais. Veja [Data Contracts](../fundacoes/quantilica-io.md#data-contracts).

### Ler cada aba suportada

```python
from rtn_fetcher import read_all_sheets

results = read_all_sheets(filepath)

for sheet_name, (data, accounts) in results.items():
    print(f"{sheet_name}: {data.nrows} data rows")
```

### Publication metadata

```python
from rtn_fetcher import fetch_publications_metadata

publications = fetch_publications_metadata()
print(publications[0])
```

## Estrutura de Dados

### Tabela de fatos (formato longo)

| Coluna  | Tipo      | Descrição                                |
|---------|-----------|--------------------------------------------|
| year    | int       | Ano de referência                             |
| month   | int       | Mês de referência (abas mensais)           |
| quarter | int       | Trimestre de referência (abas trimestrais)       |
| account | str       | Código hierárquico da conta                  |
| value   | int/float | Reais para abas de moeda; fração para % do PIB |

### Hierarquia de contas (dimensão)

| Coluna        | Tipo | Descrição                              |
|---------------|------|------------------------------------------|
| account_code  | str  | Código hierárquico (ex: `1.2.3`)        |
| account_name  | str  | Nome completo da conta                        |
| account_level | int  | Profundidade da hierarquia                          |
| P_1, P_2, ... | str  | Nome em cada nível da hierarquia             |

### Exemplo

```python
# Linhas de fatos
year  month  account  value
2024  1      1.1      1500000000
2024  1      1.2      2300000000
2024  2      1.1      1600000000

# Linhas de hierarquia
account_code  account_name             account_level  P_1       P_2
1.1           1.1 Receitas Correntes   2              Receitas  Receitas Correntes
1.2           1.2 Receitas de Capital  2              Receitas  Receitas de Capital
```

## A Classe `Tbl`

O `rtn-fetcher` vem com a `Tbl`, uma pequena tabela orientada a colunas — os dados são armazenados como uma lista de colunas em vez de linhas. Não há dependência de Polars ou Pandas; a `Tbl` é a única estrutura de dados que você precisa aprender.

```python
from rtn_fetcher import Tbl

t = Tbl([
    ["name", "Alice", "Bob"],
    ["age",  25,      30   ],
])

t["name"]                       # ["name", "Alice", "Bob"]
t.select("name")                # subconjunto
t.assign(city=["SP", "RJ"])     # adicionar/sobrescrever uma coluna
t.melt(id_cols=["name"])        # wide -> long
t.rename(name="full_name")      # renomear colunas

for row in t.iter_rows():
    print(row)
```

Principais métodos: `select`, `assign`, `melt`, `transpose`, `insert`, `drop_rows`, `drop_cols`, `rename`, `iter_rows`, `get_header`. Atributos: `data`, `nrows`, `ncols`. Todas as transformações retornam novas tabelas — as operações não são mutáveis.

## Saiba Mais

- **[Visão Geral do Tesouro](index.md)** — Todas as ferramentas do Tesouro (Finanças)
- **[tesouro-direto-fetcher](tesouro-direto-fetcher.md)** — Microdados do Tesouro Direto e análise de portfólio
- **[Tesouro Nacional — RTN](https://www.gov.br/tesouronacional/pt-br/estatisticas-fiscais-e-planejamento/resultado-do-tesouro-nacional-rtn)** — Fonte oficial
- **[API do Tesouro Nacional](https://apiapex.tesouro.gov.br/)** — API de metadados de publicações
