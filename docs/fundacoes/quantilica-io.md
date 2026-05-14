---
title: quantilica-io
description: Camada analítica da Quantilica — leitura multi-formato, conversão Parquet tipada e proveniência injetada.
---

# `quantilica-io`

Camada de processamento e padronização analítica da Quantilica. Transforma arquivos brutos baixados pelos coletores em ativos analíticos prontos para consumo — Parquet tipado, com proveniência embarcada no próprio header do arquivo.

> **Por que separado do core?** Porque processamento analítico exige Polars e PyArrow — somando 50 MB+ de dependências binárias. Quem só quer baixar dados não deveria pagar esse preço. A divisão `core` (leve) / `io` (pesado) é deliberada.

## Instalação

```bash
uv add "quantilica-io @ git+https://github.com/Quantilica/quantilica-io.git"
```

## Da bagunça ao Parquet em uma chamada

Você baixou um arquivo com um coletor Quantilica. Ao lado dele há um `.manifest.json`. Para converter para Parquet com proveniência preservada:

```python
from quantilica_core.manifests import DownloadManifest
from quantilica_io.reader import SmartReader
from quantilica_io.writer import to_parquet

manifest = DownloadManifest.from_file(
    source_id="ibge",
    dataset_id="sidra",
    url="https://servicodados.ibge.gov.br/...",
    file_path="data/raw/dataset.csv",
    producer="my-pipeline",
)

df = SmartReader().read("data/raw/dataset.csv")
to_parquet(df, "data/processed/dataset.parquet", manifest=manifest)
```

O `.parquet` resultante já contém, no próprio header (key-value metadata):

- O SHA-256 do arquivo bruto original.
- A URL de origem e o `producer` que baixou.
- O timestamp do download.
- O schema declarado (se um `DataContract` foi usado — ver seção abaixo).

Isso é **time travel real**: meses depois, você consegue provar exatamente qual versão do dado oficial foi usada em uma análise. Reprodutibilidade que sobrevive a mudanças silenciosas das fontes.

## Recursos

- **Reader multi-formato**: interface unificada para CSV, Excel, DBF (comum no DATASUS) e JSON.
- **Detecção automática de encoding**: `latin-1`, `utf-8`, `windows-1252` — sem ter que adivinhar.
- **Parquet otimizado**: compressão `zstd`, particionamento por metadados do dataset.
- **Data Contracts**: validação preventiva de schema — erro imediato se a fonte oficial alterar o layout.
- **Proveniência injetada**: manifesto do `quantilica-core` embutido no header do Parquet.

## Data Contracts

Um `DataContract` declara as colunas e tipos esperados de um dataset. Serve para dois fins:

- **Travar tipos antes de gravar Parquet.** `contract.cast(df)` força cada coluna ao dtype declarado, garantindo que Parquets do mesmo dataset tenham schemas idênticos entre execuções.
- **Detectar regressões da fonte oficial.** `contract.validate(df)` falha imediatamente se a fonte mudar nome de coluna ou tipo — você nunca grava um Parquet corrompido.

### Definindo um contrato

```python
import polars as pl
from quantilica_io.schema import DataContract, Field

SGS_CONTRACT = DataContract(
    dataset_id="bcb-sgs",
    fields=[
        Field(name="series_id", dtype=pl.Int64),
        Field(name="date", dtype=pl.Date),
        Field(name="value", dtype=pl.Float64, required=False),
        Field(name="date_end", dtype=pl.Date, required=False),
    ],
    metadata={"source": "bcb", "system": "sgs"},
)
```

`required=False` permite que a coluna esteja ausente (mas, quando presente, o tipo é validado).

### Cast: travar tipos na ingestão

```python
df = pl.DataFrame({"series_id": [11, 11], "date": [...], "value": [4.5, 4.6]})
df = SGS_CONTRACT.cast(df)
# Garante series_id=Int64, date=Date, value=Float64
to_parquet(df, "output.parquet", manifest=manifest)
```

Sem o `cast`, Polars pode inferir `Int32` em vez de `Int64` dependendo da amostra — Parquets do mesmo dataset sairiam com schemas divergentes.

### Validate: falhar cedo quando a fonte muda

```python
import pytest

def test_sgs_schema_did_not_drift():
    df = pl.read_parquet("output.parquet")
    SGS_CONTRACT.validate(df)  # ValueError ou TypeError se schema mudou
```

Quando o BCB renomear `valor` para `value_eur` em uma série, o teste falha — você descobre antes de a análise downstream produzir lixo silencioso.

### O que `validate()` faz e o que não faz

| Cobre | Não cobre |
|---|---|
| Presença de colunas obrigatórias | Range de valores (`x > 0`, `x < 100`) |
| Tipo de cada coluna | Not-null por linha |
| `DataFrame` ou `LazyFrame` | Regex / formato de string |

Para validações de valor, combine `DataContract` com Polars expressions ou Pydantic na camada de aplicação.

### Onde estão os contratos do ecossistema

| Fetcher | Contrato | Local |
|---|---|---|
| `inmet-fetcher` | `BDMEP_CONTRACT` | `inmet_fetcher.schema` |
| `bcb-sgs-fetcher` | `SGS_CONTRACT` | `bcb_sgs_fetcher.schema` |
| `rtn-fetcher` | `build_contract(sheet, cfg)` (varia por planilha) | `rtn_fetcher.schema` |

Os writers Parquet desses fetchers (`write_to_parquet`, `save_parquet`, `write_table_to_parquet`) aplicam o `cast()` automaticamente antes de gravar.

## Quando NÃO usar

- Se você só precisa **baixar** um arquivo, fique com [`quantilica-core`](quantilica-core.md). Mais leve, sem Polars.
- Se você já tem um pipeline Polars/Arrow estabelecido e não quer adotar nosso padrão de Parquet — o `to_parquet()` é opinativo de propósito.

## Princípios

1. **Reuso de boilerplate** — a lógica de lidar com `latin-1` e separador `;` do governo brasileiro é escrita **uma vez**.
2. **Interoperabilidade Parquet** — todos os arquivos gerados pelo ecossistema seguem o mesmo padrão, permitindo SQL via DuckDB sobre múltiplos datasets sem conflito de tipos.
3. **Proveniência embarcada** — o arquivo Parquet é auto-suficiente. Não precisa de um JSON ao lado para provar de onde veio.

Veja também:

- [Parquet + Polars](../concepts/parquet-polars.md) — o porquê do formato.
- [Princípios de Design](../concepts/principios.md) — Reprodutibilidade e Sem Mágica.

## Repositório

[github.com/Quantilica/quantilica-io](https://github.com/Quantilica/quantilica-io) — MIT.
