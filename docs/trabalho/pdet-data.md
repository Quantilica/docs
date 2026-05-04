# pdet-data: Buscador de Microdados de Mercado de Trabalho Brasileiro

**pdet-data** é um pacote Python para buscar, ler e converter microdados de PDET (Plataforma de Disseminação de Estatísticas do Trabalho) — plataforma oficial de estatísticas de trabalho do Brasil mantida pelo Ministério do Trabalho e Previdência Social.

Cobre RAIS (censo anual de emprego) e CAGED (fluxos mensais de emprego), incluindo CAGED legado até 2019 e CAGED redesenhado 2020+. Output é DataFrames Polars, com utilitários para bulk-convert de arquivos brutos para Parquet.

## Recursos Principais

- **FTP fetcher** — baixa tudo de `ftp.mtps.gov.br` (RAIS, CAGED, docs)
- **Smart CSV reader** — auto-detecta separator, lida com `latin-1` e `utf-8`, conserta CSVs ragged
- **Type conversion** — `INT64`, `FLOAT64`, `Boolean` e `Categorical` baseado em metadata por coluna
- **Bulk Parquet conversion** — `convert_rais` / `convert_caged` orquestram decompression + read + write
- **Schema introspection** — `extract_columns_for_dataset` dumpa todo header por arquivo para CSV
- **Polars-native** — processamento colunares rápido com dependências mínimas (`polars`, `tqdm`)

## Instalação

```bash
pip install pdet-data
```

**Requisitos:** Python 3.10+ e o CLI `7z` em `PATH` (usado por `convert_*` para extrair arquivos `.7z`).

## CLI

O pacote instala o comando `pdet-data` (também disponível como `python -m pdet_data`) com quatro subcomandos:

```text
pdet-data <subcommand> [args]

Subcomandos:
  fetch    DEST_DIR              Baixa todo arquivo RAIS e CAGED (data + docs) para DEST_DIR
  list     DEST_DIR              Lista arquivos remotos que ainda não estão presentes localmente
  convert  DATA_DIR DEST_DIR     Descomprime os arquivos brutos e escreve arquivos Parquet
  columns  DATA_DIR DATASET [-o OUT_DIR]
                                 Dumpa headers de coluna por arquivo para um dataset para CSV
```

`DATASET` para `columns` aceita: `rais-vinculos`, `rais-estabelecimentos`, `caged`, `caged-ajustes`, `caged-2020`.

## Início Rápido

### 1. Baixar todos os dados

```bash
pdet-data fetch ./data
```

Python equivalente:

```python
from pathlib import Path
from pdet_data import (
    connect,
    fetch_rais, fetch_rais_docs,
    fetch_caged, fetch_caged_docs,
    fetch_caged_2020, fetch_caged_2020_docs,
)

ftp = connect()
try:
    fetch_rais(ftp=ftp, dest_dir=Path("./data"))
    fetch_rais_docs(ftp=ftp, dest_dir=Path("./data"))
    fetch_caged(ftp=ftp, dest_dir=Path("./data"))
    fetch_caged_docs(ftp=ftp, dest_dir=Path("./data"))
    fetch_caged_2020(ftp=ftp, dest_dir=Path("./data"))
    fetch_caged_2020_docs(ftp=ftp, dest_dir=Path("./data"))
finally:
    ftp.close()
```

### 2. Converter arquivos brutos para Parquet

```bash
pdet-data convert ./data ./parquet
```

```python
from pathlib import Path
from pdet_data import convert_rais, convert_caged

convert_rais(Path("./data"), Path("./parquet"))
convert_caged(Path("./data"), Path("./parquet"))
```

### 3. Ler CSVs RAIS

```python
from pathlib import Path
import polars as pl
from pdet_data.reader import read_rais

df = read_rais(
    filepath=Path("data/rais_2023_vinculos.csv"),
    year=2023,
    dataset="vinculos",       # or "estabelecimentos"
)

top_sectors = (
    df.group_by("cnae_setor")
      .agg(pl.col("id_vinculo").count().alias("num_employees"))
      .sort("num_employees", descending=True)
      .head(10)
)
```

### 4. Ler CSVs CAGED (legado ou 2020+)

Um único `read_caged` cobre todas as variantes, despachadas pelo argumento `dataset`:

| `dataset` | Fonte | Período |
|---|---|---|
| `caged` | CAGED Legado | até 2019 |
| `caged-ajustes` | CAGED Legado — arquivos atrasados | até 2019 |
| `caged-2020-mov` | CAGED Novo — movimentos em tempo | 2020+ |
| `caged-2020-for` | CAGED Novo — arquivos atrasados | 2020+ |
| `caged-2020-exc` | CAGED Novo — exclusões | 2020+ |

```python
from pathlib import Path
import polars as pl
from pdet_data.reader import read_caged

df_caged = read_caged(
    Path("data/caged_201812.csv"),
    date=201812,
    dataset="caged",
)

df_mov = read_caged(
    Path("data/cagedmov_202401.csv"),
    date=202401,
    dataset="caged-2020-mov",
)

balance = (
    df_mov.with_columns(saldo=pl.col("admissoes") - pl.col("demissoes"))
          .group_by("uf")
          .agg(pl.col("saldo").sum())
          .sort("saldo", descending=True)
)
```

### 5. Extrair schema por arquivo

```bash
pdet-data columns ./data rais-vinculos -o ./schemas
```

```python
from pathlib import Path
from pdet_data import extract_columns_for_dataset

extract_columns_for_dataset(
    data_dir=Path("./data"),
    glob_pattern="rais-*.*",
    output_file=Path("./schemas/rais-vinculos-columns.csv"),
    encoding="latin-1",
    has_uf=True,
)
```

## Dados Disponíveis

### RAIS (Relação Anual de Informações Sociais)

Censo anual de emprego formal. Datasets: `rais-vinculos` (vínculos de emprego) e `rais-estabelecimentos` (estabelecimentos). Cobertura de 1985 até presente.

### CAGED legado

Fluxos de emprego mensais até dezembro de 2019. Datasets: `caged`, `caged-ajustes`.

### CAGED Novo (2020+)

Fluxos de emprego mensais a partir de janeiro de 2020, divididos em três arquivos por competência:

- `caged-2020-mov` — movimentos em tempo
- `caged-2020-for` — registros atrasados
- `caged-2020-exc` — exclusões / cancelamentos retroativos

## Arquitetura

```
src/pdet_data/
├── __init__.py        # Re-exporta API pública
├── __main__.py        # CLI (fetch / list / convert / columns)
├── fetch.py           # Conexão FTP, listagem, downloads
├── reader.py          # Parsing CSV + conversão de dtype
├── wrangling.py       # convert_rais, convert_caged, extract_columns_for_dataset
├── storage.py         # Convenções de caminho de destino
├── constants.py       # Schemas de coluna por ano, valores NA, lista de arquivos ragged
└── meta.py            # Diretórios FTP e padrões de nome de arquivo
```

Pipeline: FTP → arquivo comprimido (`.7z` / `.zip`) → extração `7z` → CSV → `read_rais` / `read_caged` → DataFrame Polars tipado → Parquet.

## API Pública

Importável diretamente de `pdet_data`:

| Função | Propósito |
|---|---|
| `connect()` | Abrir conexão FTP em `ftp.mtps.gov.br`. |
| `list_rais(ftp)`, `list_rais_docs(ftp)` | Iterar metadata de arquivos RAIS / docs. |
| `list_caged(ftp)`, `list_caged_docs(ftp)` | Iterar arquivos CAGED legado / docs. |
| `list_caged_2020(ftp)`, `list_caged_2020_docs(ftp)` | Iterar arquivos CAGED Novo / docs. |
| `fetch_rais(ftp, dest_dir)`, `fetch_rais_docs(...)` | Baixar dados RAIS / docs. |
| `fetch_caged(ftp, dest_dir)`, `fetch_caged_docs(...)` | Baixar dados CAGED legado / docs. |
| `fetch_caged_2020(ftp, dest_dir)`, `fetch_caged_2020_docs(...)` | Baixar dados CAGED Novo / docs. |
| `convert_rais(data_dir, dest_dir)` | Descompactar + ler + escrever Parquet para cada arquivo RAIS. |
| `convert_caged(data_dir, dest_dir)` | Mesmo para cada arquivo CAGED (legado + 2020+). |
| `extract_columns_for_dataset(...)` | Dumpar headers por arquivo para um glob de dataset. |

Helpers de leitura de baixo nível em `pdet_data.reader`:

- `read_rais(filepath, year, dataset, **read_csv_args)` — `dataset` ∈ `{"vinculos", "estabelecimentos"}`
- `read_caged(filepath, date, dataset, **read_csv_args)` — `dataset` ∈ `{"caged", "caged-ajustes", "caged-2020-mov", "caged-2020-for", "caged-2020-exc"}`
- `write_parquet(df, filepath)`
- `decompress(file_metadata)` — chamada ao binário `7z`

## Qualidade de Dados

`read_rais` / `read_caged` automaticamente:

- Detectam separador CSV (`;`, `\t`, `,`) na primeira linha
- Usam encoding correto (`latin-1` para RAIS / CAGED legado, `utf-8` para CAGED Novo)
- Removem espaço em branco e separadores de milhares de `INTEGER_COLUMNS`
- Convertem vírgulas decimais para pontos para `NUMERIC_COLUMNS`
- Fazem cast de `BOOLEAN_COLUMNS` de inteiros `0/1` para `Boolean`
- Fazem cast de todo o resto para `Categorical` depois de `strip_chars()`
- Truncam linhas muito longas em arquivos listados em `constants.RAGGED_CSV_FILES` para largura do header

## Performance

Para um ano RAIS completo (~10 GB descomprimido):

| Etapa | Tempo | Pico de memória |
|------|-----------|-------------|
| Download FTP | 5–15 min | – |
| Extração `7z` | 1–3 min | – |
| `read_rais` (parse + cast) | ~10 s | ~2 GB |
| Group-by / agg simples | <1 s | – |

*Referência: CPU moderno, 16 GB RAM, SSD.*

## Saiba Mais

- **[Dados de Comércio Exterior](../comex/comexdown.md)** — Estatísticas comerciais
- **[Arquitetura](../architecture/overview.md)** — Design do sistema
- **[PDET Oficial](http://pdet.mte.gov.br/microdados-rais-e-caged)** — Fonte governamental
