---
title: "sidra-sql — referência"
description: "Governança de revisões, ingestão streaming, API, formato TOML, schema, performance e solução de problemas do sidra-sql."
---

# sidra-sql — referência

> Parte da documentação do [sidra-sql](../sidra-sql.md). Instalação, configuração e o exemplo rápido ficam na página principal.

## Governança de Dados: Tratamento de Revisões

IBGE frequentemente publica revisões de dados. O warehouse preserva o histórico em vez de
sobrescrever, via SCD Type II nas colunas `ativo` + `modificacao` — o mecanismo de
desativar-e-inserir está detalhado em
[Bulk Load & Versionamento de Revisões](../../../conceitos/bulk-load.md). Na prática, isso permite
duas consultas:

### Consultando Snapshots Históricos

```python
from datetime import date
from sqlalchemy import select, and_
from sidra_sql.database import get_engine
from sidra_sql.config import Config
from sidra_sql.models import Dados

engine = get_engine(Config())

# Data as it existed on 2024-06-01
snapshot_date = date(2024, 6, 1)

with engine.connect() as conn:
    rows = conn.execute(
        select(Dados).where(
            and_(
                Dados.tabela_sidra_id == "1620",
                Dados.modificacao <= snapshot_date,
                Dados.ativo == True,
            )
        )
    ).fetchall()
```

### Trilha de Auditoria

```python
from sqlalchemy import select, and_
from sidra_sql.models import Dados

# Todas as versões de um ponto de dados específico
with engine.connect() as conn:
    history = conn.execute(
        select(Dados).where(
            and_(
                Dados.tabela_sidra_id == "1620",
                Dados.localidade_id == 6,
                Dados.periodo_id == 123,
            )
        ).order_by(Dados.modificacao)
    ).fetchall()

for row in history:
    status = "ATIVO" if row.ativo else "SUBSTITUÍDO"
    print(f"{row.modificacao}: {row.v}  [{status}]")
```

---

## Ingestão Streaming

A carga usa `COPY FROM STDIN` em **dois passes** (resolve dimensões em memória, depois faz
o streaming dos fatos para staging) — ~400k linhas/s, 10M linhas em segundos contra horas
com `INSERT` tradicional. O mecanismo, os diagramas e o comparativo de performance estão
em [Bulk Load & Versionamento de Revisões](../../../conceitos/bulk-load.md).

Em código, toda a carga fica atrás de um único helper:

```python
from sidra_sql.database import get_engine, load_dados
from sidra_sql.storage import Storage
from sidra_sql.config import Config

config = Config()
engine = get_engine(config)
storage = Storage.default(config)

# data_files é a lista retornada por Fetcher.download_periods(plan)
load_dados(engine, storage, data_files)  # COPY FROM STDIN, two-pass
```

---

## Referência de API

### CLI

#### Executar pipelines

```
sidra-sql run <alias> [pipeline_id] [--force-metadata]
```

Executa pipeline(s) de um plugin instalado. Omita `pipeline_id` para executar todos os pipelines do plugin. `--force-metadata` re-busca metadados da tabela SIDRA mesmo se já estiverem em cache.

```
sidra-sql run-path <path> [--force-metadata]
```

Executa um pipeline diretamente a partir de um diretório, sem plugin registrado.

```
sidra-sql transform <alias> <pipeline_id>
```

Executa apenas a etapa de transformação SQL de um pipeline (sem fetch nem load).

#### Gerenciar plugins

```
sidra-sql plugin install <url> [--alias ALIAS]
sidra-sql plugin update [alias]
sidra-sql plugin remove <alias>
sidra-sql plugin list
sidra-sql plugin validate [alias] [--plugin-dir PATH]
```

```
sidra-sql plugin scaffold <name>
    [-d/--description TEXT]
    [--version TEXT]          # padrão: 1.0.0
    [-o/--output-dir PATH]    # padrão: diretório atual
    [--git-init/--no-git-init]  # padrão: --git-init
```

Cria a estrutura de arquivos (`manifest.toml`, `fetch.toml`, `transform.toml`, `.sql`, `README.md`) para um novo plugin, com `git init` opcional.

```
sidra-sql plugin add-pipeline <pipeline_id>
    [-d/--description TEXT]
    [-p/--path PATH]          # caminho relativo ao plugin (padrão: pipeline_id)
    [--plugin-dir PATH]       # diretório raiz do plugin (padrão: diretório atual)
```

Adiciona um novo pipeline a um plugin existente, atualizando `manifest.toml`.

#### Configuração

```
sidra-sql config set <section.option> <value> [--global]
sidra-sql config get <section.option>
sidra-sql config list [--global] [--local]
```

Gerencia `config.ini`. Sem `--global`, lê/escreve o arquivo local. Com `--global`, usa `~/.config/quantilica/sidra-sql/config.ini`. O `config list` sem flags mostra a visão mesclada (local sobrescreve global).

---

### API Python (resumo)

Os pontos de entrada do pacote, na ordem de um ETL. Assinaturas completas no
[código-fonte do repositório](https://github.com/Quantilica/sidra-sql).

| Símbolo | Papel |
|---|---|
| `Config()` | Lê `config.ini` do diretório atual (storage + conexão PostgreSQL) |
| `Fetcher(config, storage=, max_workers=)` | Extração: `fetch_metadata(tabela)`, `plan_periods(tabela, territories, variables)`, `download_periods(plan)` |
| `Storage.default(config)` | Arquivos JSON locais: `write_data`, `read_data`, `write_metadata` |
| `TomlScript(config, toml_path)` | ETL declarativo: baixa + carrega as tabelas do `fetch.toml` |
| `TransformRunner(config, toml_path)` | Executa o `transform.toml` + `.sql` pareado |
| `get_engine`, `save_agregado`, `load_dados` | Helpers de banco: engine, upsert de metadados, bulk load via COPY |

---

## Formato de Pipeline TOML

### `fetch.toml` — Configuração de Extração

```toml
[[tabelas]]
tabela_sidra = "1620"          # código da tabela SIDRA (obrigatório)
variables = ["116"]             # códigos de variáveis; omitir para todas
territories = {6 = []}          # {nível: [códigos]}; lista vazia = todas
unnest_classifications = true   # expandir todos os cross-produtos de categorias

[[tabelas]]
tabela_sidra = "1737"
variables = ["63"]
territories = {1 = [], 3 = []}
split_variables = true          # uma requisição por variável (evita limites SIDRA)
classifications = {81 = ["allxt"]}
```

**Campos de `[[tabelas]]`:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|------------|----------|
| `tabela_sidra` | str | ✅ | Código da tabela SIDRA |
| `territories` | dict[str, list] | ✅ | Nível territorial → códigos de unidade |
| `variables` | list[str] | | Códigos de variáveis (padrão: todas) |
| `classifications` | dict[str, list] | | Classificação → códigos de categorias |
| `unnest_classifications` | bool | | Expandir todas as combinações de categorias |
| `split_variables` | bool | | Uma requisição por variável |

### `transform.toml` — Configuração de Transformação

```toml
[[table]]
name = "pib_municipal"          # nome da tabela/view alvo
schema = "analytics"            # schema alvo
strategy = "replace"            # "replace" (tabela) ou "view"
sql = "transform.sql"           # arquivo .sql pareado
description = "PIB Municipal"
primary_key = ["municipio_id", "ano"]
indexes = [
  { name = "idx_pib_ano", columns = ["ano"], unique = false }
]
```

Pareado com arquivo `transform.sql` (mesmo nome) contendo consulta SELECT.

### `manifest.toml` — Registro de Plugin

```toml
name = "Pipelines Padrão"
description = "Pipelines SIDRA padrão Quantilica"
version = "1.0.0"

[[pipeline]]
id = "pib_municipal"
description = "PIB Municipal da tabela SIDRA 5938 IBGE"
path = "pib_municipal"
```

---

## Schema Dimensional

O star schema (diagrama acima) vive no schema `ibge_sidra`: três dimensões —
`localidade` (malha territorial), `periodo` (tempo normalizado com
`ano`/`mes`/`trimestre`/`data_inicio`/`data_fim`) e `dimensao` (variável × até 6
classificações) — mais a tabela-fato enxuta `dados` (FKs + `modificacao` + `ativo` + `v`) e
o registro `tabela_sidra` (metadados em JSONB). As colunas e constraints completas de cada
tabela estão nos [modelos SQLAlchemy do repositório](https://github.com/Quantilica/sidra-sql).

### Exemplo de Consulta Analítica

```python
from sqlalchemy import select
from sidra_sql.models import Dados, Localidade, Periodo, Dimensao

# PIB por estado: tabela 5938 (PIB dos Municípios, anual, com níveis N1, N2, N3 e N6),
# variável 37 (PIB a preços correntes), apenas registros ativos
query = (
    select(
        Localidade.d1n.label("estado"),
        Periodo.codigo.label("periodo"),
        Dimensao.d2n.label("variavel"),
        Dados.v.label("valor"),
    )
    .join(Localidade, Dados.localidade_id == Localidade.id)
    .join(Periodo,    Dados.periodo_id    == Periodo.id)
    .join(Dimensao,   Dados.dimensao_id   == Dimensao.id)
    .where(
        Dados.ativo == True,
        Localidade.nc == "N3",          # estados
        Dados.tabela_sidra_id == "5938",
        Dimensao.d2c == "37",           # PIB a preços correntes
    )
    .order_by(Periodo.codigo.desc())
)

with engine.connect() as conn:
    for row in conn.execute(query):
        print(f"{row.estado} | {row.periodo} | {row.valor}")
```

---

## Performance

### Cache Local

Dados baixados são armazenados como arquivos JSON sob `data_dir`. Re-executar um pipeline
pula arquivos que já existem em disco:

```
Primeira execução:  baixa do IBGE (segundos a minutos)
Re-execução:        verifica cache local, pula arquivos existentes (overhead <1s)
```

Force re-download deletando o diretório de dados. A flag `--force-metadata` renova apenas os metadados.

## Melhores Práticas para Governança de Dados

### 1. Use Pipelines Declarativos (TOML) para Reprodutibilidade

```toml
# pipelines/annual_snapshot/fetch.toml
[[tabelas]]
tabela_sidra = "1620"
variables = ["116"]
territories = {6 = [], 3 = []}

[[tabelas]]
tabela_sidra = "1737"
variables = ["63"]
territories = {1 = []}
```

Vantagens:

- ✅ Não-desenvolvedores podem manter pipelines
- ✅ Controle de versão (TOML em git)
- ✅ Reprodutível entre máquinas
- ✅ Desacoplado de mudanças de código

### 2. Documente Datas de Snapshot para Reprodutibilidade Acadêmica

```python
import json
from datetime import datetime

# Registrar quando você construiu o dataset
metadata = {
    "snapshot_date": datetime.now().isoformat(),
    "pipeline": "pipelines/analysis/fetch.toml",
    "sidra_sql_version": "1.2.0",
}
with open("data/metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)
```

Então consulte com `Dados.modificacao <= snapshot_date` para reproduzir o dataset exato.

### 3. Use Star Schema para Ferramentas BI

Conecte PostgreSQL diretamente a:

- **Tableau** (conexão ODBC para PostgreSQL)
- **Power BI** (conector nativo PostgreSQL)
- **Looker** (SQL runner)
- **Metabase** (consultas SQL em warehouse)

Schema normalizado é otimizado para workloads OLAP de ferramentas BI.

---

## Resolução de Problemas

### Download Falha com Erro de Rede

`Fetcher` retenta automaticamente (até 5 vezes, backoff exponencial: 5s → 10s → 20s…).
Se todas as tentativas falharem, verifique disponibilidade da API SIDRA ou reduza `max_workers`.

### Tabela Não Encontrada

Códigos de tabela SIDRA devem ser strings, não inteiros. Use `"1620"`, não `1620`.

```python
metadata = fetcher.fetch_metadata("1620")   # ✅
metadata = fetcher.fetch_metadata(1620)     # ❌ por convenção (o código converte com int())
```

### ID de Variável Desconhecido

Procure no catálogo SIDRA IBGE diretamente em [sidra.ibge.gov.br](https://sidra.ibge.gov.br/)
para procurar códigos de variáveis e classificações para uma tabela dada.

### Arquivo de Configuração Não Encontrado

`Config()` lê `config.ini` do diretório de trabalho atual.
Execute Python da raiz do projeto, ou defina o caminho explicitamente:

```python
import os
os.chdir("/path/to/project")
config = Config()
```

### Schema Já Existe

`TransformRunner` com `strategy = "replace"` descarta e recria a tabela alvo.
`strategy = "view"` usa `CREATE OR REPLACE VIEW` e é não-destrutivo.
