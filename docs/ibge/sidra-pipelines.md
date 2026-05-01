# sidra-pipelines

**Official catalog of pre-built ETL pipelines for the sidra-sql motor.**

## What It Is

`sidra-pipelines` is the standard library of 14 production-ready data pipelines for the `sidra-sql` motor. It's a single Git repository containing declarative TOML + SQL definitions for the most commonly-used IBGE datasets.

Instead of writing your own pipeline definitions, install this catalog and run pre-built extractions with a single CLI command:

```bash
sidra-sql run std pib_municipal    # PIB dos Municípios
sidra-sql run std ipca             # Inflation (IPCA)
sidra-sql run std ppm_rebanhos     # Livestock herds (PPM)
```

No code to write. No configuration to manage. Just data.

## Architecture

```
┌─────────────────────────────────────────────┐
│     sidra-pipelines (This Repository)       │
│  • manifest.toml (pipeline registry)        │
│  • 14 directories (one per pipeline)        │
│  • Each with: fetch.toml + transform.sql    │
└────────────────┬────────────────────────────┘
                 │
                 │  sidra-sql plugin install <url> --alias std
                 │
┌────────────────▼────────────────────────────┐
│         sidra-sql Motor                     │
│  reads manifest → orchestrates fetch/load   │
└────────────────┬────────────────────────────┘
                 │
        ┌────────┴─────────┐
        ▼                  ▼
    SIDRA API          PostgreSQL
   (raw data)         (normalized
                       + analytics)
```

## Included Pipelines

The catalog covers 14 essential Brazilian economic, demographic, and agricultural datasets:

### 📊 Economics & Prices

| Pipeline ID | Research | SIDRA Table | Output Table |
|---|---|---|---|
| `pib_municipal` | **GDP by Municipality** | 5938 | `analytics.pib_municipal` |
| `ipca` | **IPCA** (Consumer inflation) | 7060, 1419, ... | `analytics.ipca` |
| `ipca15` | **IPCA-15** (Mid-month inflation) | 7062, 1705, ... | `analytics.ipca15` |
| `inpc` | **INPC** (Wage-earner inflation) | 7063, 1100, ... | `analytics.inpc` |

### 👥 Demographics

| Pipeline ID | Research | SIDRA Table | Output Table |
|---|---|---|---|
| `estimativa_populacao` | **Population Estimates** | 6579 | `analytics.estimativa_populacao` |
| `censo_populacao` | **Census (Demographic Census)** | 200 | `analytics.censo_populacao` |
| `contagem_populacao` | **Population Count** | 305, 793 | `analytics.contagem_populacao` |

### 🌾 Agriculture & Forestry

| Pipeline ID | Research | SIDRA Table | Output Table |
|---|---|---|---|
| `pam_lavouras_temporarias` | **PAM** (Temporary crops) | 839, 1000, ... | `analytics.pam_lavouras_temporarias` |
| `pam_lavouras_permanentes` | **PAM** (Permanent crops) | 1613 | `analytics.pam_lavouras_permanentes` |
| `ppm_rebanhos` | **PPM** (Livestock herds) | 73, 3939 | `analytics.ppm_rebanhos` |
| `ppm_producao` | **PPM** (Animal production) | 74, 3940 | `analytics.ppm_producao` |
| `ppm_exploracao` | **PPM** (Aquaculture) | 94, 95 | `analytics.ppm_exploracao` |
| `pevs_producao` | **PEVS** (Forest/timber production) | 289, 291 | `analytics.pevs_producao` |
| `pevs_area_florestal` | **PEVS** (Forest area) | 5930 | `analytics.pevs_area_florestal` |

## Installation

### 1. Install sidra-sql

```bash
git clone https://github.com/Quantilica/sidra-sql.git
cd sidra-sql
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Configure Database

Create `config.ini` in the working directory:

```ini
[storage]
data_dir = data

[database]
user          = postgres
password      = your_password
host          = localhost
port          = 5432
dbname        = dados
schema        = ibge_sidra
tablespace    = pg_default
readonly_role = readonly_role
```

### 3. Install This Catalog

```bash
sidra-sql plugin install https://github.com/Quantilica/sidra-pipelines.git --alias std
```

Verify installation:

```bash
sidra-sql plugin list
```

## Quick Start

### Execute a Pipeline

```bash
# Download GDP data and create analytics table
sidra-sql run std pib_municipal

# Expected output:
# ✓ Fetching metadata for table 5938
# ✓ Downloading periods (2002–2022)
# ✓ Loading 4,537 rows into ibge_sidra.dados
# ✓ Running transformation SQL
# ✓ Created analytics.pib_municipal (4,537 rows)
```

### Query the Result

```sql
-- Analytics table is ready for Power BI, Metabase, SQL queries
SELECT
    ano,
    id_municipio,
    variavel,
    unidade,
    valor
FROM analytics.pib_municipal
WHERE ano >= 2020
ORDER BY id_municipio, ano DESC;
```

### Run All Pipelines

```bash
# Download and transform all 14 datasets
for pipeline in pib_municipal ipca inpc estimativa_populacao ppm_rebanhos pam_lavouras_temporarias pevs_producao; do
    sidra-sql run std $pipeline
done
```

## Pipeline Structure

Each pipeline is a directory with three files:

### fetch.toml

Specifies which SIDRA tables and variables to download:

```toml
[[tabelas]]
sidra_tabela = "5938"           # GDP table ID
variables    = ["37"]           # GDP variable
territories  = {6 = ["all"]}   # All municipalities
```

### transform.toml

Configures the output analytics table:

```toml
[table]
name        = "pib_municipal"
schema      = "analytics"
strategy    = "replace"
description = "GDP at current prices, annual by municipality"
primary_key = ["ano", "id_municipio"]
```

### transform.sql

SQL SELECT that denormalizes the raw data:

```sql
SELECT
    p.ano                                              AS ano,
    l.d1c                                              AS id_municipio,
    dim.d2n                                            AS variavel,
    dim.mn                                             AS unidade,
    CASE WHEN d.v ~ '^-?[0-9]' THEN d.v::numeric END   AS valor
FROM dados d
JOIN periodo    p   ON d.periodo_id    = p.id
JOIN dimensao   dim ON d.dimensao_id   = dim.id
JOIN localidade l   ON d.localidade_id = l.id
WHERE d.sidra_tabela_id = '5938'
  AND d.ativo = true;
```

## Extending: Add Your Own Pipeline

To add a new dataset to this catalog:

### 1. Create a directory

```bash
mkdir meu-novo-indicador
cd meu-novo-indicador
```

### 2. Write fetch.toml

Find the SIDRA table ID on [sidra.ibge.gov.br](https://sidra.ibge.gov.br), then define:

```toml
[[tabelas]]
sidra_tabela = "XXXX"
variables    = ["YY"]
territories  = {6 = ["all"]}
```

### 3. Write transform.toml

```toml
[table]
name   = "meu_indicador"
schema = "analytics"
```

### 4. Write transform.sql

```sql
SELECT /* your denormalization query */
```

### 5. Register in manifest.toml

At the repository root:

```toml
[[pipeline]]
id          = "meu_novo_indicador"
description = "My custom indicator"
fetch       = "meu-novo-indicador/fetch.toml"
transform   = "meu-novo-indicador/transform.toml"
```

### 6. Test & Push

```bash
sidra-sql run std meu_novo_indicador
git add .
git commit -m "Add meu-novo-indicador pipeline"
git push
```

Then contribute back via Pull Request!

## Performance Notes

### First-Time Run

First execution downloads all historical data. Depending on table size:

- **Small tables** (inflation): 10–30 seconds
- **Medium tables** (agriculture): 1–5 minutes
- **Large tables** (census): 5–15 minutes

### Subsequent Runs

Cache hit for unchanged data = near-instant completion.

### Optimization Tips

1. **Filter dates in fetch.toml** — Don't fetch all history if you only need recent data
2. **Run pipelines in parallel** — Multiple `sidra-sql run` commands can run concurrently
3. **Use PostgreSQL properly** — Index the analytics tables for faster queries

## Use Cases

### 📈 Economic Monitoring

Track Brazil's macroeconomic performance in real time:

```sql
SELECT periodo, variavel, valor
FROM analytics.ipca
WHERE periodo >= '202401'
ORDER BY periodo DESC;
```

### 📊 Analytical Reporting

Build dashboards in Power BI, Metabase, or Superset:

```
Analytics tables ready for immediate BI import:
├── analytics.pib_municipal
├── analytics.ipca
├── analytics.ipca15
├── analytics.inpc
├── analytics.estimativa_populacao
└── ... (8 more)
```

### 🔬 Academic Research

Download clean, normalized historical data:

```sql
SELECT * FROM analytics.censo_populacao
WHERE ano IN (1991, 2000, 2010, 2020);
```

### 🌾 Agricultural Analysis

Analyze crop production and livestock:

```sql
SELECT
    id_municipio,
    variavel,
    SUM(valor) AS total_producao
FROM analytics.pam_lavouras_temporarias
GROUP BY id_municipio, variavel
ORDER BY total_producao DESC;
```

## Troubleshooting

### "Plugin not found"

```bash
# Verify installation
sidra-sql plugin list

# Reinstall if missing
sidra-sql plugin install https://github.com/Quantilica/sidra-pipelines.git --alias std
```

### "Table not found" (404)

SIDRA table IDs change occasionally. Check the official portal:

- [SIDRA Database](https://sidra.ibge.gov.br/)
- Update the `fetch.toml` with the correct table ID

### Slow downloads

- API may be rate-limited during peak hours; retry later
- Use a recent Python version (3.11+) for better performance
- Check your internet connection

### PostgreSQL connection error

Verify `config.ini`:

- Database exists: `createdb dados`
- User has permissions: `ALTER USER postgres WITH PASSWORD 'password';`
- Connection: `psql -U postgres -h localhost -d dados`

## Contributing

Missing a dataset? Follow the steps in [Extending](#extending-add-your-own-pipeline), then open a Pull Request!

## Learn More

- **sidra-sql Motor:** [Quantilica/sidra-sql](https://github.com/Quantilica/sidra-sql)
- **Creating pipelines guide:** [CREATING_PIPELINES.md](https://github.com/Quantilica/sidra-sql/blob/main/CREATING_PIPELINES.md)
- **SIDRA Portal:** [sidra.ibge.gov.br](https://sidra.ibge.gov.br/)
- **IBGE Official:** [ibge.gov.br](https://www.ibge.gov.br/)
