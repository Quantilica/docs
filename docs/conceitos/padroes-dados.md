---
title: Padrões práticos de dados
description: "Parquet em vez de CSV, lazy evaluation, gestão de memória e documentação de transformações: os padrões de dados do ecossistema em código real."
---

# Padrões Práticos de dados

Complemento de [Padrões Práticos de execução](padroes.md). Cobre os quatro padrões que tratam do **formato e do volume** dos dados, cada um ligado a um [Princípio de Design](principios.md).

| Padrão | Princípio principal |
|---|---|
| [Parquet em vez de CSV](#parquet-vs-csv) | Performance, Reprodutibilidade |
| [Lazy evaluation](#lazy-evaluation) | Performance |
| [Gestão de memória para arquivos grandes](#memoria-arquivos-grandes) | Performance |
| [Documentação e reprodutibilidade](#documentacao-reprodutibilidade) | Reprodutibilidade, Sem Mágica |

---

## Parquet em vez de CSV {#parquet-vs-csv}

**Definição:** Parquet é formato colunar otimizado para análise. CSV é formato textual baseado em linhas, dos anos 70.

### Por quê?

- **82% a 87% menor** nos dados medidos (RAIS 2024, Centro-Oeste: 2,2 GiB de CSV → 406 MiB de Parquet).
- **Rápido para ler o que importa**: o formato colunar pula colunas e linhas irrelevantes; com filtro e 3 colunas, a leitura foi 51× a 100× mais rápida que a do CSV tipado nos dados medidos.
- **Tipado**: sem adivinhar se uma coluna é string ou número.
- **Comprimido**: compressão embutida; sem `.gz` separado.

### Padrão: converter e ler seletivamente

Converta uma vez (`pl.read_csv(...).write_parquet(...)`) e, nas análises, leia só as colunas de que precisa (`pl.read_parquet(path, columns=[...])`): o CSV obrigaria a ler todas. Os exemplos completos estão em [Parquet + Polars](parquet-polars.md#início-rápido).

### Padrão: bulk convert

```bash
# pdet-fetcher: descompacta cada .7z, faz parse com schema por-ano, escreve Parquet
quantilica pdet convert -i ./raw -o ./parquet
```

```python
import polars as pl

# Após converter, mantenha tudo em Parquet para análise
df = pl.read_parquet("parquet/rais-vinculos/rais-vinculos_2023@*.parquet")
# CSV apenas para compartilhar com stakeholders não-técnicos
```

---

## Lazy evaluation {#lazy-evaluation}

**Definição:** lazy evaluation adia a computação até ser explicitamente requisitada. O otimizador de query simplifica suas operações antes de executá-las.

### Por quê?

- **Otimização**: o otimizador combina múltiplas operações em pass único.
- **Eficiência de memória**: processe 100M linhas sem carregar tudo em RAM.
- **Execução mais rápida**: trabalho desnecessário é eliminado automaticamente.

### Padrão: consultas lazy

Prefira `pl.scan_parquet(...)` a `pl.read_parquet(...)` em arquivos grandes: o otimizador empurra filtros e seleção de colunas para a leitura e agrega em passe único. O exemplo comentado está em [Parquet + Polars](parquet-polars.md#workflows-eficientes-em-memória).

### Padrão: concatenação multi-ano

```python
import polars as pl

# ❌ Ineficiente: agrega por ano, depois combina (14 agregações)
years_data = []
for year in range(2010, 2024):
    df = pl.read_parquet(f"rais_{year}.parquet")
    agg = df.group_by("sector").agg(pl.col("salary").mean())
    years_data.append(agg)
combined = pl.concat(years_data)

# ✅ Eficiente: concatena primeiro, agrega uma vez
years_data = []
for year in range(2010, 2024):
    df = pl.read_parquet(f"rais_{year}.parquet").with_columns(
        pl.lit(year).alias("year")
    )
    years_data.append(df)

combined = pl.concat(years_data, how="vertical")
by_sector = (
    combined.lazy()
    .group_by(["year", "sector"])
    .agg(pl.col("salary").mean())
    .collect()
)
```

---

## Gestão de memória para arquivos grandes {#memoria-arquivos-grandes}

**Definição:** processe arquivos grandes sem carregar tudo em RAM. Use streaming/chunking ou lazy evaluation.

### Por quê?

- **RAIS é 50M+ linhas**: não cabe em Pandas em máquinas típicas.
- **Siscomex é GB**: abordagem ingênua causa OOM.
- **Streaming é gratuito**: sem penalidade — frequentemente até mais rápido.

### Padrão: streaming chunks

```bash
# O download é feito em streaming (chunks de 64 KiB) pelo cliente HTTP do core:
# memória constante, independente do tamanho do arquivo, e escrita atômica
# via arquivo temporário renomeado no sucesso.
quantilica comex sync trade-exp -o ./DATA
```

### Padrão: lazy e streaming no Polars

Para Parquet maior que a RAM, use `pl.scan_parquet(...)` com `.collect(engine="streaming")`. Veja o exemplo em [Parquet + Polars](parquet-polars.md#streaming-para-volumes-maiores-que-a-ram).

### Padrão: CSV em chunks

```python
import polars as pl

chunk_size = 1_000_000

all_results = []
for chunk in pl.read_csv_batched("large_file.csv", batch_size=chunk_size):
    result = chunk.group_by("state").agg(pl.col("salary").mean())
    all_results.append(result)

combined = pl.concat(all_results)
```

---

## Documentação e reprodutibilidade {#documentacao-reprodutibilidade}

**Definição:** documente seus dados — de onde vêm, quando foram buscados, como foram transformados, como reproduzir.

### Por quê?

- **Trilha de auditoria**: saiba exatamente quais dados estão na sua análise.
- **Reprodutibilidade**: outros podem verificar seus resultados.
- **Debugging**: quando algo quebra, você sabe o que mudou.

### Padrão: metadados ao lado do Parquet

```python
import json
from datetime import datetime
from pathlib import Path
import polars as pl

parquet_path = next(Path("parquet/rais-vinculos").glob("rais-vinculos_2023@*.parquet"))
df = pl.read_parquet(parquet_path)

metadata = {
    "source": "RAIS 2023 (vinculos)",
    "download_timestamp": datetime.now().isoformat(),
    "fetch_method": "pdet_fetcher.convert_rais",
    "row_count": df.height,
    "columns": df.columns,
    "transformations": [
        "Descomprimido via 7z",
        "CSV parseado com schema por-ano (pdet_fetcher.reader.read_rais)",
        "Cast INTEGER_COLUMNS / NUMERIC_COLUMNS / BOOLEAN_COLUMNS",
        "Escrito Parquet via polars.DataFrame.write_parquet",
    ],
}
parquet_path.with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2))
```

### Padrão: extração de documentação na fonte

```sh
# Baixar dados + livros de códigos + tabelas auxiliares juntos
quantilica datasus sync -o ./data sim-do-cid10 --start 2023 --end 2023 --docs --aux
```

Os arquivos `.dbc` são gravados como `{dataset}_{AAAAMM}-{uf}@{AAAAMMDD}.dbc`, com a data de modificação da fonte após o `@`, então múltiplas revisões DATASUS coexistem em disco. `datasus-fetcher archive --archive-data-dir ./archive` rotaciona versões antigas sem perdê-las.

### Padrão: log de transformação

```python
import logging
import polars as pl

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("pipeline.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

df = pl.read_parquet("rais_2023.parquet")
initial = len(df)
logger.info(f"Carregado RAIS 2023: {initial:,} linhas")

df = df.filter(pl.col("salary") > 0)
logger.info(f"Filtrado para {len(df):,} (removidas {initial - len(df):,} inválidas)")

result = df.group_by("state").agg(pl.col("salary").mean())
logger.info(f"Agregado por estado: {len(result)} estados")

result.write_parquet("output.parquet")
logger.info("Salvo em output.parquet")
```

---

## Checklist resumo

- [ ] **Parquet**: armazene resultados em Parquet, não CSV.
- [ ] **Lazy**: use lazy evaluation para datasets grandes.
- [ ] **Memória**: stream ou chunk para arquivos grandes.
- [ ] **Documente**: registre transformações e metadados.

---

## Saiba mais

- [Padrões Práticos de execução](padroes.md) — idempotência, concorrência, retry, validação e UX de CLI.
- [Princípios de Design](principios.md) — por que estes padrões existem.
- [Parquet + Polars](parquet-polars.md) — tutorial focado no formato/biblioteca centrais.
