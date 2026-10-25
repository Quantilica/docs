---
title: "bcb-sgs-sql — referência"
description: "Histórico sem auditoria, ingestão streaming, API, formato TOML, schema, performance e solução de problemas do bcb-sgs-sql."
---

# bcb-sgs-sql — referência

> Parte da documentação do [bcb-sgs-sql](../bcb-sgs-sql.md). Instalação, configuração e o exemplo rápido ficam na página principal.

## Governança de Dados: Histórico sem Auditoria

O BCB revisa valores. O warehouse preserva o histórico em vez de sobrescrever — e **sem**
uma tabela de auditoria separada — via soft-versioning nas colunas `ativo` + `loaded_at`.
O mecanismo de detecção-de-mudança (desativar-e-inserir, com no-op em recargas idênticas)
está detalhado em [Bulk Load & Versionamento de Revisões](../../../conceitos/bulk-load.md). Na
prática, isso permite duas consultas:

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

## Ingestão Streaming

Como a série é plana (sem dimensões com FK), a carga é **single-pass**: `COPY FROM STDIN`
para staging, depois *deactivate-then-insert* (desativar a versão anterior antes de inserir
a revisão, satisfazendo o índice único parcial). O mecanismo e a comparação com o modelo
em dois passes do SIDRA estão em
[Bulk Load & Versionamento de Revisões](../../../conceitos/bulk-load.md).

Toda a carga fica atrás de um único helper, que retorna a contagem de mudanças:

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
`~/.config/quantilica/bcb-sgs-sql/config.ini`. `config list` sem flags mostra a visão mesclada.

---

### API Python (resumo)

Os pontos de entrada do pacote, agrupados pelas duas vias de acoplamento. Assinaturas
completas no [código-fonte do repositório](https://github.com/Quantilica/bcb-sgs-sql).

| Símbolo | Papel |
|---|---|
| `Config()` | Lê `config.ini` do diretório atual (storage + conexão PostgreSQL) |
| `sgs.Fetcher(storage, max_workers=)` | **Via A**: `plan_series`, `fetch_metadata`, `download_series` |
| `loader.load(config, path, kind=)` | **Via B**: carrega JSON de observações/metadados em disco, sem rede |
| `TomlScript(config, toml_path)` | ETL declarativo: metadados → observações → carga |
| `TransformRunner(config, toml_path)` | Executa o `transform.toml` + `.sql` pareado |
| `database.*` | `get_engine`, `create_all`, `save_series_metadata`, `load_series_data` (COPY soft-versioned) |

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

Quatro tabelas no schema configurado (ex.: `bcb_sgs`), criadas por
`database.create_all(engine, schema)` — o diagrama está acima:

- **`series_metadata`** — catálogo da série (nomes, frequência, unidade, fonte,
  `theme_hierarchy` com índice GIN, `search_vector` para busca full-text).
- **`series_data`** — tabela-fato soft-versioned (`series_id`, `date`, `date_end`, `value`,
  `loaded_at`, `ativo`), com índice único parcial
  `(series_id, date, date_end) NULLS NOT DISTINCT WHERE ativo` — no máximo uma linha ativa
  por chave.
- **`theme`** — hierarquia de temas auto-referente (`name`, `level`, `parent_id`).
- **`arquivo_carregado`** — rastreador de arquivos para a idempotência da Via B.

As colunas e constraints completas estão nos
[modelos SQLAlchemy do repositório](https://github.com/Quantilica/bcb-sgs-sql).

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
