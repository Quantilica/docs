---
title: bcb-sgs-sql — Data warehouse PostgreSQL para séries do BCB SGS
description: Camada SQL/ETL sobre o bcb-sgs-fetcher — carrega catálogo, temas e observações do SGS em PostgreSQL com soft-versioning (histórico de revisões sem tabela de auditoria), via fetch-and-load ou load-from-files.
---

# bcb-sgs-sql

**Camada de ETL e Data Warehousing para as séries temporais do BCB SGS em PostgreSQL.**

!!! warning "Pegadinhas da fonte e do carregamento"

    - **O BCB revisa valores sem aviso.** Uma observação publicada hoje pode mudar numa próxima divulgação. O `bcb-sgs-sql` usa *soft-versioning* (`ativo`, `loaded_at`) — nunca sobrescreve; insere uma nova revisão e marca a anterior `ativo = FALSE`. A "verdade atual" é `WHERE ativo = TRUE`; a trilha de revisões é `ORDER BY loaded_at`.
    - **Requer PostgreSQL ≥ 15.** O índice único parcial usa `NULLS NOT DISTINCT` para tratar `date_end IS NULL` (séries diárias) como mesma chave. Em versões anteriores seria preciso uma coluna gerada de chave.
    - **Séries diárias têm download retroativo.** A API `/dados` não devolve o histórico completo de alta frequência; o `bcb-sgs-fetcher` faz a varredura ano a ano. Não é o `bcb-sgs-sql` que reimplementa isso — ele apenas passa o acrônimo de frequência.
    - **Metadados exigem scraping com sessão stateful.** O catálogo vem do `ScraperClient` (HTML), que mantém cookies — **não** é seguro paralelizar a coleta de metadados.
    - **`config.ini` lê do CWD.** Rodar de outro diretório falha sem mensagem clara. Use caminho absoluto ou `os.chdir()`.

## O Que É

**`bcb-sgs-sql`** é a infraestrutura de Data Warehousing e ETL para os dados do **SGS**
(Sistema Gerenciador de Séries Temporais) do Banco Central do Brasil. É a camada SQL
análoga ao `sidra-sql` do IBGE.

Enquanto **bcb-sgs-fetcher** resolve o problema de comunicação (obter séries da API JSON e
metadados via scraping), **bcb-sgs-sql** resolve o problema de **persistência, governança
e reprodutibilidade**: converte observações e metadados do SGS em um banco PostgreSQL
relacional, com histórico de revisões preservado — sem depender da aplicação privada
`aplicação privada`.

## Problema que Resolve

Levar séries do SGS para análise rigorosa ou modelagem envolve desafios além do download:

### 1. Catálogo, observações e temas em um modelo coerente

O SGS tem mais de 17.000 séries, cada uma com metadados ricos (nome, frequência, unidade,
fonte, hierarquia de temas) e um histórico de observações `(data, valor)`. O `bcb-sgs-sql`
separa isso em três tabelas — `series_metadata` (catálogo), `series_data` (observações) e
`theme` (hierarquia auto-referente) — em vez de achatar tudo num CSV que perde integridade.

### 2. Gargalos de I/O de ingestão

Séries longas (diárias com décadas de histórico) acumulam milhões de observações. Inserção
linha a linha via ORM é lenta e gasta RAM. O motor usa `COPY FROM STDIN` + tabela de
staging.

### 3. Revisões & reprodutibilidade — sem tabela de auditoria

O BCB revisa valores. Sobrescrever destrói a reprodutibilidade. A aplicação privada
`aplicação privada` resolve isso com overwrite + uma tabela `audit_log`. O `bcb-sgs-sql`
adota uma abordagem mais enxuta: **soft-versioning na própria tabela-fato**, preservando a
trilha completa de revisões sem nenhuma tabela de auditoria separada.

## Arquitetura & Recursos Principais

### 1. Dois caminhos de acoplamento (Via A e Via B)

O pacote serve tanto quem quer buscar-e-carregar num passo só quanto quem já tem os
artefatos em disco:

```mermaid
graph LR
    subgraph A [Via A — fetch-and-load]
        A1[bcb-sgs-fetcher API/scraper] --> A2[sgs.Fetcher]
        A2 --> A3[load_series_data]
    end
    subgraph B [Via B — load-from-files]
        B1[JSON em disco] --> B2[loader.load]
        B2 --> A3
    end
    A3 --> DB[(PostgreSQL)]
```

- **Via A** (`run`, `run-path`): `sgs.Fetcher` envolve o `SgsDataClient` (valores) e o
  `ScraperClient` (metadados), com cache em disco e retry/backoff.
- **Via B** (`load`): lê arquivos JSON de observações e de metadados já em disco — **sem
  rede** — e carrega no banco. Permite usar o pacote 100% sobre artefatos.

Ambas convergem em `database.load_series_data`, então a lógica de soft-versioning vive em
um único lugar.

### 2. Ingestão Streaming (COPY)

- **PostgreSQL `COPY FROM STDIN`**: transmite as observações para uma tabela temporária
  `_staging_series_data`.
- **Single-pass**: como a série temporal é plana (sem dimensões com FK a resolver), não há
  o "Pass 1" de coleta do SIDRA.
- **Stubs de catálogo**: `_ENSURE_SERIES` cria linhas mínimas em `series_metadata` para
  satisfazer a FK numa carga values-only.

### 3. Soft-versioning por detecção-de-mudança (SCD na própria fato)

Auditabilidade sem tabela de auditoria:

- **Nunca sobrescreve**: quando o valor de uma observação muda, insere uma nova linha
  (`ativo = TRUE`, `loaded_at` da execução) e marca a anterior `ativo = FALSE`.
- **Detecção-de-mudança**: só insere/desativa quando o valor **difere** do ativo corrente.
  Recargas idênticas são um no-op (zero churn).
- **Invariante no banco**: um índice único parcial garante no máximo uma linha ativa por
  `(series_id, date, date_end)`.

```mermaid
erDiagram
    theme ||--o{ series_metadata : theme_id
    series_metadata ||--o{ series_data : series_id

    theme {
        int id PK
        text name
        int level
        int parent_id FK
    }
    series_metadata {
        int series_id PK
        text name
        text frequency_acronym
        text unit
        text_array theme_hierarchy
        int theme_id FK
        tsvector search_vector
    }
    series_data {
        bigint id PK
        int series_id FK
        date date
        date date_end
        numeric value
        timestamptz loaded_at
        boolean ativo
    }
```

### 4. Pipelines declarativos via TOML

Lógica de negócio isolada de código, igual ao `sidra-sql`:

```toml
# fetch.toml — quais séries carregar
[[series]]
ids = [433, 13522, 189]          # IPCA mensal, IPCA acum. 12m, IGP-M

[[series]]
themes = ["Índices de preços"]   # filtra o catálogo (exige catálogo já carregado)
frequency = "M"                   # opcional: D, S, M, T, Qd, A
```

### 5. Hierarquia de temas

A `theme_hierarchy` de cada série (ex.: `["Preços", "Índices", "IPCA"]`) é normalizada numa
árvore auto-referente (`theme`) **e** mantida denormalizada como ARRAY (com índice GIN)
para consultas de containment rápidas.

### 6. Arquitetura de plugin

O motor é genérico; os pipelines vivem em repositórios Git separados (ex.:
`bcb-sgs-pipelines`):

```
Plugin (seu repo Git)
├── manifest.toml       ← registro de pipelines
├── precos/ipca/
│   ├── fetch.toml      ← quais séries baixar do SGS
│   ├── transform.toml  ← config da tabela analytics
│   └── ipca.sql        ← consulta wide-pivot
```

```bash
bcb-sgs-sql plugin install https://github.com/Quantilica/bcb-sgs-pipelines.git --alias std
bcb-sgs-sql run std precos
```

### Recursos Adicionais

- ✅ Busca full-text no catálogo (`search_vector` tsvector português + inglês)
- ✅ Cache de metadados (`{id:06d}_basic.json` / `_full.json`, interoperável com o fetcher)
- ✅ Integração PostgreSQL (transações ACID)
- ✅ Operações idempotentes (recarga segura, zero churn)
- ✅ Retry com backoff exponencial (até 5 tentativas)
- ✅ Histórico de revisões via colunas `ativo` + `loaded_at` (sem `audit_log`)

## Instalação

```bash
pip install git+https://github.com/Quantilica/bcb-sgs-sql.git
```

Com [uv](https://github.com/astral-sh/uv):

```bash
uv add "git+https://github.com/Quantilica/bcb-sgs-sql.git"
```

## Configuração

`bcb-sgs-sql` lê um `config.ini` no diretório de trabalho:

```ini
[storage]
data_dir = data

[database]
user = postgres
password = suasenha
host = localhost
port = 5432
dbname = dados
schema = bcb_sgs
```

Carregue a config em Python:

```python
from bcb_sgs_sql.config import Config

config = Config()  # lê config.ini do diretório atual
```

Ou via CLI:

```bash
bcb-sgs-sql config set database.host     localhost
bcb-sgs-sql config set database.port     5432
bcb-sgs-sql config set database.user     postgres
bcb-sgs-sql config set database.password suasenha
bcb-sgs-sql config set database.dbname   dados
bcb-sgs-sql config set database.schema   bcb_sgs
bcb-sgs-sql config set storage.data_dir  data
```

## Exemplo Rápido: Pipeline ETL

### Opção 1: CLI com plugin (Via A)

Use pipelines pré-construídos de `bcb-sgs-pipelines`:

```bash
# Instalar catálogo padrão
bcb-sgs-sql plugin install https://github.com/Quantilica/bcb-sgs-pipelines.git --alias std

# Executar pipeline (buscar metadados + observações + carregar + transformar)
bcb-sgs-sql run std precos

# Consultar resultados em PostgreSQL
psql -c "SELECT * FROM analytics.precos ORDER BY date DESC LIMIT 12"
```

### Opção 2: Load-from-files (Via B, sem rede)

Carrega artefatos já baixados pelo `bcb-sgs-fetcher`:

```bash
# Detecta automaticamente JSON de observações / metadados
bcb-sgs-sql load ./data/bcb-sgs --kind auto

# Ou explicitamente
bcb-sgs-sql load ./data/bcb-sgs/data --kind json
bcb-sgs-sql load ./data/bcb-sgs/metadata --kind metadata
```

### Opção 3: TOML declarativo

Define o fetch:

```toml
# pipelines/precos/fetch.toml
[[series]]
ids = [433, 13522, 189]
```

Define a transform (wide-pivot — uma coluna por série):

```toml
# pipelines/precos/transform.toml
[[table]]
name = "precos"
schema = "analytics"
strategy = "replace"
sql = "precos.sql"
```

```sql
-- pipelines/precos/precos.sql
SELECT
    sd.date,
    MAX(CASE WHEN sd.series_id = 433   THEN sd.value END) AS ipca_mensal,
    MAX(CASE WHEN sd.series_id = 13522 THEN sd.value END) AS ipca_acum_12m,
    MAX(CASE WHEN sd.series_id = 189   THEN sd.value END) AS igpm_mensal
FROM series_data sd
WHERE sd.series_id IN (433, 13522, 189)
  AND sd.ativo = TRUE
GROUP BY sd.date
ORDER BY sd.date;
```

Execute:

```python
from pathlib import Path
from bcb_sgs_sql.config import Config
from bcb_sgs_sql.toml_runner import TomlScript
from bcb_sgs_sql.transform_runner import TransformRunner

config = Config()

# Extract + Load (metadados → observações → banco)
TomlScript(config, Path("pipelines/precos/fetch.toml")).run()

# Transform (SQL → schema analytics)
TransformRunner(config, Path("pipelines/precos/transform.toml")).run()
```

### Opção 4: ETL programático

```python
from bcb_sgs_sql.config import Config
from bcb_sgs_sql import database, sgs

config = Config()
engine = database.get_engine(config)
database.create_all(engine)

with sgs.Fetcher(config.data_dir, max_workers=4) as fetcher:
    series_ids = [433, 13522]

    # 1. Metadados (catálogo + temas)
    rows = []
    freq_by_id = {}
    for sid in series_ids:
        basic, full = fetcher.fetch_metadata(sid)
        with engine.begin() as conn:
            theme_id = database.upsert_theme_hierarchy(
                conn, basic.theme_hierarchy
            )
        # ... mapear para linha de catálogo (ver loader.basic_to_metadata_row)

    # 2. Observações
    points = fetcher.download_series(series_ids, frequency_by_id=freq_by_id)

# 3. Carregar (soft-versioned)
rows = [(p.series_id, p.date, p.date_end, p.value) for p in points]
database.load_series_data(engine, rows)
```

## Governança de Dados: Histórico sem Auditoria

O BCB revisa valores. O warehouse preserva o histórico em vez de sobrescrever — e **sem**
uma tabela de auditoria separada.

### Como funciona o soft-versioning

**Cenário**: o valor do IPCA de 2020-01-01 muda numa nova divulgação.

```sql
-- Carga inicial: 1 linha ativa
-- series_data: id=1, series_id=433, date='2020-01-01', value=0.21,
--              loaded_at='2024-01-01', ativo=TRUE

-- Nova carga com valor revisado (0.25). database.load_series_data:
-- 1. _DEACTIVATE — desativa a anterior (valor difere)
UPDATE series_data SET ativo = FALSE
WHERE series_id = 433 AND date = '2020-01-01'
  AND date_end IS NOT DISTINCT FROM NULL
  AND ativo = TRUE AND value IS DISTINCT FROM 0.25;

-- 2. _INSERT — insere a revisão como nova linha ativa
INSERT INTO series_data (series_id, date, date_end, value, loaded_at, ativo)
VALUES (433, '2020-01-01', NULL, 0.25, now(), TRUE);
```

Recarregar o mesmo valor é um no-op: nem desativa, nem insere (zero churn).

### Consultando a verdade atual

```sql
SELECT date, value
FROM series_data
WHERE series_id = 433 AND ativo = TRUE
ORDER BY date;
```

### Trilha de revisão de uma observação

```python
import sqlalchemy as sa
from bcb_sgs_sql import database, models
from bcb_sgs_sql.config import Config

engine = database.get_engine(Config())

with engine.connect() as conn:
    stmt = (
        sa.select(
            models.SeriesData.value,
            models.SeriesData.loaded_at,
            models.SeriesData.ativo,
        )
        .where(
            models.SeriesData.series_id == 433,
            models.SeriesData.date == "2020-01-01",
        )
        .order_by(models.SeriesData.loaded_at)
    )
    for row in conn.execute(stmt):
        status = "ATIVO" if row.ativo else "SUBSTITUÍDO"
        print(f"{row.loaded_at:%Y-%m-%d}: {row.value}  [{status}]")
```

---

## Ingestão Streaming: COPY + detecção-de-mudança

### Problema: INSERT tradicional

```python
# ❌ Inserção linha-por-linha (abordagem ingênua)
for sid, date, date_end, value in observations:
    conn.execute(insert(series_data).values(...))
conn.commit()
# Lento + I/O de milhões de round-trips
```

### Solução: COPY para staging, depois deactivate-then-insert

```mermaid
graph TD
    S1[COPY observações → _staging_series_data] --> S2[_ENSURE_SERIES: stubs de catálogo]
    S2 --> S3[_DEACTIVATE: ativa anterior vira FALSE se valor difere]
    S3 --> S4[_INSERT: linhas novas/alteradas viram ativa]
```

A ordem importa: desativar **antes** de inserir garante que a chave revisada não tenha
linha ativa no momento do INSERT, satisfazendo o índice único parcial.

### Exemplo de uso

```python
from bcb_sgs_sql import database
from bcb_sgs_sql.config import Config

engine = database.get_engine(Config())

# rows = [(series_id, date, date_end, value), ...]
n_staging, n_inserted, n_deactivated = database.load_series_data(engine, rows)
print(f"{n_inserted} inseridas, {n_deactivated} desativadas")
```

---

## Referência de API

### CLI

#### Executar pipelines (Via A)

```
bcb-sgs-sql run <alias> [pipeline_id] [--force-metadata] [--force-load]
```

Executa pipeline(s) de um plugin instalado. Omita `pipeline_id` para rodar todos.
`--force-metadata` re-busca metadados mesmo se em cache.

```
bcb-sgs-sql run-path <path> [--force-metadata] [--force-load]
```

Executa um pipeline diretamente de um diretório, sem plugin registrado.

```
bcb-sgs-sql transform <alias> <pipeline_id>
```

Executa apenas a etapa de transformação SQL (sem fetch nem load).

#### Carregar arquivos (Via B)

```
bcb-sgs-sql load <path> [--kind json|metadata|auto] [--force-load]
```

Carrega dados de arquivos em disco no PostgreSQL, **sem rede**. `--kind auto` detecta pelo
conteúdo do diretório (metadados `*_basic.json` ou JSON de observações).

#### Gerenciar plugins

```
bcb-sgs-sql plugin install <url> [--alias ALIAS]
bcb-sgs-sql plugin update [alias]
bcb-sgs-sql plugin remove <alias>
bcb-sgs-sql plugin list
bcb-sgs-sql plugin validate [alias] [--plugin-dir PATH]
```

```
bcb-sgs-sql plugin scaffold <name>
    [-d/--description TEXT]
    [--version TEXT]            # padrão: 1.0.0
    [-o/--output-dir PATH]      # padrão: diretório atual
    [--git-init/--no-git-init]  # padrão: --git-init
```

Cria a estrutura (`manifest.toml`, `fetch.toml`, `transform.toml`, `.sql`, `README.md`)
para um novo plugin.

```
bcb-sgs-sql plugin add-pipeline <pipeline_id>
    [-d/--description TEXT]
    [-p/--path PATH]
    [--plugin-dir PATH]
```

Adiciona um pipeline a um plugin existente, atualizando `manifest.toml`.

#### Configuração

```
bcb-sgs-sql config set <section.option> <value> [--global]
bcb-sgs-sql config get <section.option>
bcb-sgs-sql config list [--global] [--local]
```

Gerencia `config.ini`. Sem `--global`, lê/escreve o arquivo local; com `--global`, usa
`~/.config/bcb-sgs-sql/config.ini`. `config list` sem flags mostra a visão mesclada.

---

### `Config` — Configuração em Tempo de Execução

```python
from bcb_sgs_sql.config import Config

config = Config()  # lê config.ini
```

| Atributo | Chave ini | Descrição |
|-----------|---------|-------------|
| `config.data_dir` | `storage.data_dir` | Raiz de armazenamento local |
| `config.db_user` | `database.user` | Usuário PostgreSQL |
| `config.db_password` | `database.password` | Senha PostgreSQL |
| `config.db_host` | `database.host` | Host PostgreSQL |
| `config.db_port` | `database.port` | Porta PostgreSQL |
| `config.db_name` | `database.dbname` | Nome do banco |
| `config.db_schema` | `database.schema` | Schema (ex.: `bcb_sgs`) |

---

### `sgs.Fetcher` — Extração de Dados (Via A)

```python
from bcb_sgs_sql import sgs
from bcb_sgs_sql.storage import Storage

storage = Storage.default(config)

with sgs.Fetcher(storage, max_workers=4) as fetcher:
    ...
```

**Métodos principais:**

| Método | Propósito |
|--------|-----------|
| `fetcher.plan_series(selectors, engine=None)` | Resolve `[[series]]` (ids/themes/frequency) numa lista de IDs |
| `fetcher.fetch_metadata(series_id, force=False)` | `(SeriesMetadataBasic, SeriesMetadataFull)`, com cache |
| `fetcher.download_series(series_ids, frequency_by_id=None)` | Baixa observações em paralelo; retorna `list[SeriesPoint]` |

---

### `loader` — Carregamento de Arquivos (Via B)

```python
from pathlib import Path
from bcb_sgs_sql import loader

loader.load(config, Path("./data/bcb-sgs"), kind="auto")
```

**Funções principais:**

| Função | Propósito |
|--------|-----------|
| `loader.load(config, path, kind="auto", force_load=False)` | Entry point do comando `load` |
| `loader.load_metadata_dir(config, path)` | Carrega `{id}_basic.json` / `_full.json` + temas |
| `loader.load_observations(config, files, force_load=False)` | Carrega JSON de observações |
| `loader.read_json_rows(path)` | Lê tuplas de um JSON (`series_id`/`date`/`value`/`date_end`) |
| `loader.basic_to_metadata_row(basic, full=None, ...)` | Mapeia dataclass → linha de catálogo |

---

### `Storage` — Gerenciamento de Arquivos Locais

```python
from bcb_sgs_sql.storage import Storage

storage = Storage.default(config)   # usa config.data_dir
storage = Storage("/custom/path")   # raiz explícita
```

| Método | Propósito |
|--------|-----------|
| `storage.write_series_data(rows, series_id, stamp)` | Salva observações como JSON |
| `storage.read_series_data(filepath)` | Lê arquivo de observações |
| `storage.read_series_dir()` | Última versão por série no diretório |
| `storage.write_metadata(series_id, basic=, full=)` | Salva metadados JSON |
| `storage.read_basic_metadata(series_id)` / `read_full_metadata` | Lê metadados em cache |
| `storage.has_basic_metadata(series_id)` | Verifica cache de metadados |

---

### `TomlScript` — Executor de ETL Declarativo

```python
from pathlib import Path
from bcb_sgs_sql.toml_runner import TomlScript

script = TomlScript(
    config,
    toml_path=Path("pipelines/precos/fetch.toml"),
    max_workers=4,
    force_metadata=False,
    force_load=False,
)
script.run()  # metadados → observações → carga
```

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|----------|
| `config` | Config | | Configuração |
| `toml_path` | Path | | Caminho para `fetch.toml` |
| `max_workers` | int | 4 | Threads de download |
| `force_metadata` | bool | False | Re-buscar metadados em cache |
| `force_load` | bool | False | Recarregar arquivos já registrados |

---

### `TransformRunner` — Executor de Transformação SQL

```python
from bcb_sgs_sql.transform_runner import TransformRunner

runner = TransformRunner(config, toml_path=Path("pipelines/precos/transform.toml"))
runner.run()
```

Lê `transform.toml` + `.sql` pareado; materializa o resultado como tabela (`replace`) ou
view (`view`). Idêntico ao `sidra-sql`.

---

### `database` — Auxiliares de Banco de Dados

```python
from bcb_sgs_sql import database

engine = database.get_engine(config)
database.create_all(engine)                          # cria tabelas
database.upsert_theme_hierarchy(conn, hierarchy)     # árvore de temas (idempotente)
database.save_series_metadata(engine, rows)          # upsert do catálogo
database.load_series_data(engine, rows)              # carga soft-versioned via COPY
database.get_loaded_filenames(engine, names)         # idempotência por arquivo
```

`load_series_data` retorna `(n_staging, n_inserted, n_deactivated)`.

---

## Formato de Pipeline TOML

### `fetch.toml` — Seleção de Séries

```toml
[[series]]
ids = [433, 13522, 189]          # IDs de séries SGS (sempre válido)

[[series]]
themes = ["Índices de preços"]   # filtra o catálogo (exige catálogo já carregado)
frequency = "M"                   # opcional: D, S, M, T, Qd, A
```

**Campos de `[[series]]`:**

| Campo | Tipo | Descrição |
|-------|------|----------|
| `ids` | list[int] | IDs de séries (sempre válido) |
| `themes` | list[str] | Filtra séries cujo `theme_hierarchy` contém o tema |
| `frequency` | str | Restringe `themes` por acrônimo de frequência |

Cada `[[series]]` precisa de `ids` **ou** `themes`. Selectors `themes`/`frequency` exigem
um catálogo já populado (rode os metadados antes).

### `transform.toml` — Configuração de Transformação

```toml
[[table]]
name = "precos"
schema = "analytics"
strategy = "replace"            # "replace" (tabela) ou "view"
sql = "precos.sql"
description = "Painel wide de índices de preços"
primary_key = ["date"]
indexes = [
  { name = "idx_precos_date", columns = ["date"], unique = false }
]
```

Idêntico ao `sidra-sql`. Pareado com um `.sql` contendo a SELECT.

### `manifest.toml` — Registro de Plugin

```toml
name = "Pipelines BCB SGS"
description = "Pipelines SGS padrão Quantilica"
version = "1.0.0"

[[pipeline]]
id = "precos"
description = "Índices de preços (IPCA, IGP-M)"
path = "precos"
```

---

## Schema

Tabelas criadas no schema configurado (ex.: `bcb_sgs`) por
`Base.metadata.create_all(engine)`.

**`series_metadata`** — Catálogo de séries

| Coluna | Tipo | Descrição |
|--------|------|----------|
| `series_id` | integer PK | ID natural da série no SGS (não auto) |
| `name`, `name_abbreviated`, `name_english`, `name_english_abbreviated` | text | Nomes |
| `theme_hierarchy` | text[] | Caminho de temas (índice GIN) |
| `frequency_acronym` | text | D / S / M / T / Qd / A |
| `frequency`, `unit`, `source` | text | Frequência, unidade, fonte |
| `start_date`, `last_date`, `last_date_index` | date | Janela de disponibilidade |
| `series_type`, `precision`, `max_value`, `min_value` | — | Descritores |
| `active`, `special`, `formula`, `series_primitive` | — | Flags/derivação |
| `owner_manager`, `message`, `message_warning` | text | Gestor, avisos |
| `full_provider_data`, `full_description`, `full_methodology`, `full_dissemination_formats` | jsonb | Metadados completos |
| `last_update` | date | Última atualização de metadados |
| `theme_id` | integer FK | → `theme.id` (`ON DELETE SET NULL`) |
| `search_vector` | tsvector | Busca full-text (gerado, índice GIN) |

**`series_data`** — Tabela de fatos (soft-versioned)

| Coluna | Tipo | Descrição |
|--------|------|----------|
| `id` | bigint PK | Auto-incremento |
| `series_id` | integer FK | → `series_metadata.series_id` |
| `date` | date | Data da observação |
| `date_end` | date \| null | Data final (frequências não-diárias) |
| `value` | numeric | Valor (precisão preservada) |
| `loaded_at` | timestamptz | Carimbo da revisão |
| `ativo` | boolean | Flag de registro ativo |

Índice único parcial: `(series_id, date, date_end) NULLS NOT DISTINCT WHERE ativo` —
no máximo uma linha ativa por chave.

**`theme`** — Hierarquia de temas (auto-referente)

| Coluna | Tipo | Descrição |
|--------|------|----------|
| `id` | integer PK | Auto-incremento |
| `name` | text | Nome do tema |
| `level` | integer | Profundidade (1 = raiz) |
| `parent_id` | integer FK | → `theme.id` |

Constraints: `level > 0`; `(parent_id IS NULL) = (level = 1)`; único
`(name, level, parent_id)`.

**`arquivo_carregado`** — Rastreador de arquivos (idempotência da Via B)

| Coluna | Tipo | Descrição |
|--------|------|----------|
| `arquivo` | text PK | Nome do arquivo carregado |
| `series_id` | integer FK \| null | Série (nullable: um arquivo pode conter várias) |
| `carregado_em` | timestamptz | Quando foi carregado |

### Exemplo de consulta: painel wide

```sql
-- Uma coluna por série, indexado por data (apenas registros ativos)
SELECT
    sd.date,
    MAX(CASE WHEN sd.series_id = 11  THEN sd.value END) AS selic,
    MAX(CASE WHEN sd.series_id = 12  THEN sd.value END) AS cdi,
    MAX(CASE WHEN sd.series_id = 433 THEN sd.value END) AS ipca
FROM series_data sd
WHERE sd.series_id IN (11, 12, 433)
  AND sd.ativo = TRUE
GROUP BY sd.date
ORDER BY sd.date;
```

---

## Performance

### Cache Local

Observações e metadados baixados pela Via A ficam em `data_dir`. Metadados em cache são
reutilizados (a menos de `--force-metadata`). A Via B nunca toca a rede.

### Ingestão via COPY

`COPY FROM STDIN` para staging + INSERT em lote evita o overhead de inserção linha a linha.
Como o modelo é plano (sem dimensões), a carga é single-pass.

## Melhores Práticas

### 1. Use pipelines declarativos (TOML) para reprodutibilidade

```toml
# pipelines/juros/fetch.toml
[[series]]
ids = [11, 12]   # Selic, CDI (diárias)
```

- ✅ Não-desenvolvedores mantêm pipelines
- ✅ Versionável em git
- ✅ Reprodutível entre máquinas

### 2. Consulte snapshots por `loaded_at`

Para reproduzir o estado dos dados numa data, filtre por `loaded_at` (a trilha de revisões
fica toda na `series_data`).

### 3. Use o schema relacional para ferramentas BI

Conecte PostgreSQL diretamente a Tableau, Power BI, Looker, Metabase. As views wide-pivot
do `transform.toml` são ideais como fonte.

---

## Resolução de Problemas

### Requer PostgreSQL ≥ 15

O índice único parcial usa `NULLS NOT DISTINCT`, disponível a partir do PostgreSQL 15.

### Selector `themes` retorna vazio

`themes`/`frequency` consultam o catálogo. Rode os metadados antes (ex.: um pipeline com
`ids`, ou `load --kind metadata`) para popular `series_metadata`.

### Séries diárias demoram

A estratégia retroativa do `bcb-sgs-fetcher` faz múltiplas requisições ano a ano. É
esperado para séries diárias longas.

### Arquivo de Configuração Não Encontrado

`Config()` lê `config.ini` do diretório atual. Rode da raiz do projeto ou ajuste:

```python
import os
os.chdir("/path/to/project")
config = Config()
```

---

## Saiba Mais

- [Visão Geral BCB](index.md)
- [bcb-sgs-fetcher](bcb-sgs-fetcher.md) — Ferramenta de extração de séries
- [sidra-sql](../ibge/sidra-sql.md) — O análogo para o IBGE/SIDRA
- [Princípios de Design](../concepts/principios.md)
- [SGS — Sistema Gerenciador de Séries Temporais](https://www3.bcb.gov.br/sgspub/)
- [Documentação PostgreSQL](https://www.postgresql.org/docs/)
