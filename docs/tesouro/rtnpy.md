# rtnpy — Resultado do Tesouro Nacional (RTN) Brasileiro

**rtnpy** é um pacote Python que baixa, extrai e normaliza o *Resultado do Tesouro Nacional* (RTN) — relatório mensal de resultados fiscais federais do Brasil. Transforma as pastas de trabalho Excel com múltiplas abas do Tesouro em tabelas de formato longo limpo com expansão hierárquica de contas, prontas para análise ou carregamento em warehouse.

## O Que É

O *Resultado do Tesouro Nacional* contém dados fiscais consolidados do Governo Federal Brasileiro: receitas, despesas e resultado primário, em valores correntes e constantes, mensais, trimestrais e anuais, também como percentuais do PIB. O Tesouro publica isso como uma extensa pasta de trabalho Excel com 24+ abas, cada uma com seu próprio layout de header e hierarquia de contas. `rtnpy` automatiza o pipeline de fetch-and-normalize para você ir da URL oficial a uma tabela de formato longo arrumada em poucas linhas de Python — ou um comando CLI.

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
- CLI para fetch e exportação Excel/SQLite

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

Requer Python 3.13+.

```bash
pip install rtnpy
# ou
uv add rtnpy
```

Dependências: `httpx`, `openpyxl`, `beautifulsoup4`.

## Interface de Linha de Comando

O pacote instala um comando `rtnpy` com subcomandos `fetch` e `export`:

```bash
rtnpy --help

# Operações de fetch
rtnpy fetch metadata          # Construir metadata.json da página de publicações
rtnpy fetch download          # Baixar arquivos listados em metadata.json
rtnpy fetch latest            # Baixar a pasta de trabalho RTN mais recente

# Operações de export
rtnpy export excel            # Exportar para uma pasta de trabalho Excel formatada
rtnpy export sqlite           # Exportar para um banco de dados SQLite
```

### Opções de Buscar

```bash
rtnpy fetch metadata --dest data --force
rtnpy fetch download --metadata data/metadata.json --concurrency 8
rtnpy fetch latest   --dest data
```

### Opções de Export

```bash
rtnpy export excel  --data-dir data --output rtn_data.xlsx
rtnpy export sqlite --data-dir data --output rtn_data.db
```

Ambos os comandos `export` baixam a pasta de trabalho mais recente e escrevem todas as abas suportadas junto com a dimensão de hierarquia de contas.

## API Python

### Baixar

```python
from pathlib import Path
from rtnpy import download_latest_file

filepath = download_latest_file(Path("data"))
print(f"Baixado: {filepath}")
```

`download_latest_file` retorna o `Path` do arquivo baixado, ou `None` se uma cópia atual já existe no destino.

### Ler uma aba única

```python
from pathlib import Path
from rtnpy import read_sheet, write_table_to_csv

filepath = Path("data/rtn_202412301200.xlsx")
data, accounts = read_sheet(filepath, "1.2")

print(f"Dados:     {data.nrows} linhas x {data.ncols} colunas")
print(f"Contas:    {accounts.nrows} linhas x {accounts.ncols} colunas")

write_table_to_csv(data,     Path("output/rtn_1_2_data.csv"))
write_table_to_csv(accounts, Path("output/rtn_1_2_accounts.csv"))
```

`read_sheet(filepath, sheet_name)` retorna uma tupla `(data, accounts)` de instâncias `Tbl` — a tabela de fatos em formato longo e a dimensão de hierarquia de contas.

### Ler cada aba suportada

```python
from rtnpy import read_all_sheets

results = read_all_sheets(filepath)

for sheet_name, (data, accounts) in results.items():
    print(f"{sheet_name}: {data.nrows} data rows")
```

### Publication metadata

```python
from rtnpy import fetch_publications_metadata

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

O `rtnpy` vem com a `Tbl`, uma pequena tabela orientada a colunas — os dados são armazenados como uma lista de colunas em vez de linhas. Não há dependência de Polars ou Pandas; a `Tbl` é a única estrutura de dados que você precisa aprender.

```python
from rtnpy import Tbl

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
- **[tddata](tddata.md)** — Microdados do Tesouro Direto e análise de portfólio
- **[Tesouro Nacional — RTN](https://www.gov.br/tesouronacional/pt-br/estatisticas-fiscais-e-planejamento/resultado-do-tesouro-nacional-rtn)** — Fonte oficial
- **[API do Tesouro Nacional](https://apiapex.tesouro.gov.br/)** — API de metadados de publicações
