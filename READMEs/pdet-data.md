# 📊 pdet-data

> Ferramenta para coletar, processar e analisar microdados de emprego e trabalho do Brasil diretamente da **PDET** (Plataforma de Disseminação de Estatísticas do Trabalho).

Acesse dados do **RAIS** e **CAGED** de forma programática, com conversão automática de tipos, tratamento de anomalias e exportação para Parquet.

---

## ⚡ O que é a PDET?

A **PDET** é a plataforma oficial do Ministério do Trabalho e Previdência Social (MTPS) que disponibiliza os microdados de trabalho do Brasil:

- 📋 **RAIS** (Relação Anual de Informações Sociais): vínculos de emprego formal e estabelecimentos, por ano
- 💼 **CAGED** (Cadastro Geral de Empregados e Desempregados): movimentações mensais (admissões, demissões)

Esses microdados são essenciais para análises de mercado de trabalho, pesquisa acadêmica e inteligência de negócios.

---

## 🎯 Por que usar `pdet-data`?

### Desafios com os dados brutos

Os microdados da PDET vêm em formatos legados (`.7z`, `.zip`) com características específicas:

- Colunas com tipos mal definidos (números com espaços e pontos)
- CSVs "ragged" com número inconsistente de colunas
- Codificações `latin-1` (RAIS, CAGED clássico) e `utf-8` (CAGED 2020)
- Estruturas de colunas que mudam entre anos

### O que essa ferramenta oferece

✅ **Acesso direto via FTP**: conecta a `ftp.mtps.gov.br` e baixa todos os arquivos
✅ **Detecção automática**: separador, codificação, esquema por ano
✅ **Conversão de tipos**: strings → INT64/FLOAT64/BOOLEAN/Categorical
✅ **Correção de ragged CSVs**: trunca linhas longas para o tamanho do header
✅ **Conversão para Parquet** via `convert_rais` / `convert_caged`
✅ **Extração de schema** via `extract_columns_for_dataset`
✅ **Performance**: processamento Polars
✅ **Dependências mínimas**: apenas `polars` e `tqdm` (binário externo `7z` para descompactar)

---

## 📦 Instalação

```bash
pip install pdet-data
```

Em modo editável:

```bash
git clone https://github.com/Quantilica/pdet-data.git
cd pdet-data
pip install -e .
```

**Requisitos**: Python 3.10+ e `7z` no PATH (para descompactar os arquivos baixados).

---

## 🛠️ CLI

O pacote instala o comando `pdet-data` (também acessível via `python -m pdet_data`) com quatro subcomandos:

```text
pdet-data <subcommand> [args]

Subcommands:
  fetch    DEST_DIR              Baixa todo o RAIS e CAGED (dados + docs) para DEST_DIR
  list     DEST_DIR              Lista no FTP o que ainda falta baixar em DEST_DIR
  convert  DATA_DIR DEST_DIR     Descompacta e converte CSVs em Parquet
  columns  DATA_DIR DATASET [-o OUT_DIR]
                                 Extrai os nomes de colunas de cada arquivo do dataset
```

`DATASET` em `columns` aceita: `rais-vinculos`, `rais-estabelecimentos`, `caged`, `caged-ajustes`, `caged-2020`.

---

## 🚀 Uso Rápido

### 1️⃣ Baixar todos os microdados

```bash
pdet-data fetch ./dados
```

Equivalente em Python:

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
    fetch_rais(ftp=ftp, dest_dir=Path("./dados"))
    fetch_rais_docs(ftp=ftp, dest_dir=Path("./dados"))
    fetch_caged(ftp=ftp, dest_dir=Path("./dados"))
    fetch_caged_docs(ftp=ftp, dest_dir=Path("./dados"))
    fetch_caged_2020(ftp=ftp, dest_dir=Path("./dados"))
    fetch_caged_2020_docs(ftp=ftp, dest_dir=Path("./dados"))
finally:
    ftp.close()
```

### 2️⃣ Converter os arquivos brutos para Parquet

```bash
pdet-data convert ./dados ./parquet
```

Equivalente em Python:

```python
from pathlib import Path
from pdet_data import convert_rais, convert_caged

convert_rais(Path("./dados"), Path("./parquet"))
convert_caged(Path("./dados"), Path("./parquet"))
```

### 3️⃣ Ler dados RAIS (baixo nível)

```python
from pathlib import Path
import polars as pl
from pdet_data.reader import read_rais

# Vínculos de emprego de 2023
df = read_rais(
    filepath=Path("dados/rais_2023_vinculos.csv"),
    year=2023,
    dataset="vinculos",   # ou "estabelecimentos"
)

top_setores = (
    df.group_by("cnae_setor")
      .agg(pl.col("id_vinculo").count().alias("n_vinculos"))
      .sort("n_vinculos", descending=True)
      .head(10)
)
print(top_setores)
```

### 4️⃣ Ler dados CAGED (clássico ou 2020+)

`read_caged` lê todas as variantes através do parâmetro `dataset`:

| `dataset` | Origem | Período |
|---|---|---|
| `caged` | CAGED clássico | até 2019 |
| `caged-ajustes` | CAGED clássico — declarações fora do prazo | até 2019 |
| `caged-2020-mov` | Novo CAGED — movimentações no prazo | 2020+ |
| `caged-2020-for` | Novo CAGED — fora do prazo | 2020+ |
| `caged-2020-exc` | Novo CAGED — exclusões | 2020+ |

```python
from pathlib import Path
import polars as pl
from pdet_data.reader import read_caged

# CAGED clássico de dezembro/2018
df_caged = read_caged(
    Path("dados/caged_201812.csv"),
    date=201812,
    dataset="caged",
)

# Novo CAGED — movimentações de janeiro/2024
df_mov = read_caged(
    Path("dados/cagedmov_202401.csv"),
    date=202401,
    dataset="caged-2020-mov",
)

# Saldo por UF
saldo = (
    df_mov.with_columns(saldo=pl.col("admissoes") - pl.col("demissoes"))
          .group_by("uf")
          .agg(pl.col("saldo").sum())
          .sort("saldo", descending=True)
)
print(saldo)
```

### 5️⃣ Extrair o esquema de colunas de um dataset

```bash
pdet-data columns ./dados rais-vinculos -o ./schemas
```

Equivalente em Python:

```python
from pathlib import Path
from pdet_data import extract_columns_for_dataset

extract_columns_for_dataset(
    data_dir=Path("./dados"),
    glob_pattern="rais-*.*",
    output_file=Path("./schemas/rais-vinculos-columns.csv"),
    encoding="latin-1",
    has_uf=True,
)
```

---

## 📚 Dados Disponíveis

### RAIS (Relação Anual de Informações Sociais)

**O que é**: base de referência com todos os vínculos de emprego formal do Brasil, declarados anualmente pelos empregadores.

**Frequência**: anual

**Datasets**:

- `rais-vinculos` — informações sobre cada relação de emprego (salário, ocupação, setor)
- `rais-estabelecimentos` — dados das empresas/órgãos (CNPJ, endereço, setor econômico)

**Casos de uso**: análise de renda por região/setor/ocupação, estudos de empregabilidade, desigualdade de gênero/raça, dinâmica de empresas.

### CAGED clássico

**O que é**: registro de fluxo mensal de emprego.

**Frequência**: mensal

**Datasets**: `caged`, `caged-ajustes`

**Período**: até dezembro de 2019

### Novo CAGED (CAGED 2020)

**O que é**: nova versão do CAGED, a partir de janeiro/2020, com três variantes:

- `caged-2020-mov` — movimentações declaradas no prazo
- `caged-2020-for` — declaradas fora do prazo
- `caged-2020-exc` — exclusões (cancelamentos retroativos)

---

## 🏗️ Arquitetura

```
src/pdet_data/
├── __init__.py        # Re-exports da API pública
├── __main__.py        # CLI (fetch / list / convert / columns)
├── fetch.py           # Conexão FTP, listagem e download
├── reader.py          # Leitura e tipagem dos CSVs
├── wrangling.py       # convert_rais, convert_caged, extract_columns_for_dataset
├── storage.py         # Convenções de caminhos no destino
├── constants.py       # Schemas de colunas, NA values, ragged files
└── meta.py            # Metadados (caminhos no FTP, padrões de filename)
```

### Fluxo de dados

```
FTP (ftp.mtps.gov.br)
    ↓  fetch_*
arquivos compactados (.7z, .zip)
    ↓  convert_* (chama 7z para extrair)
CSVs (latin-1 ou utf-8, separador detectado)
    ↓  read_rais / read_caged
DataFrame Polars com tipos corretos
    ↓  write_parquet
Parquet
```

---

## 🔧 API pública

Todas estas funções são importáveis diretamente de `pdet_data`:

| Função | Descrição |
|---|---|
| `connect()` | Conecta ao FTP da PDET (`ftp.mtps.gov.br`). |
| `list_rais(ftp)` / `list_rais_docs(ftp)` | Lista arquivos RAIS / documentação. |
| `list_caged(ftp)` / `list_caged_docs(ftp)` | Lista CAGED clássico / docs. |
| `list_caged_2020(ftp)` / `list_caged_2020_docs(ftp)` | Lista Novo CAGED / docs. |
| `fetch_rais(ftp, dest_dir)` / `fetch_rais_docs(...)` | Baixa RAIS / documentação. |
| `fetch_caged(ftp, dest_dir)` / `fetch_caged_docs(...)` | Baixa CAGED clássico / docs. |
| `fetch_caged_2020(ftp, dest_dir)` / `fetch_caged_2020_docs(...)` | Baixa Novo CAGED / docs. |
| `convert_rais(data_dir, dest_dir)` | Descompacta e grava RAIS em Parquet. |
| `convert_caged(data_dir, dest_dir)` | Descompacta e grava CAGED em Parquet. |
| `extract_columns_for_dataset(...)` | Extrai os nomes de coluna de cada arquivo do dataset. |

Funções de leitura de baixo nível em `pdet_data.reader`:

- `read_rais(filepath, year, dataset, **read_csv_args)` — `dataset` ∈ `{"vinculos", "estabelecimentos"}`
- `read_caged(filepath, date, dataset, **read_csv_args)` — `dataset` ∈ `{"caged", "caged-ajustes", "caged-2020-mov", "caged-2020-for", "caged-2020-exc"}`
- `write_parquet(df, filepath)`
- `decompress(file_metadata)` — invoca o binário `7z` para extrair

---

## 📊 Exemplos de Análise

### 1. Setores que mais empregam (RAIS 2023)

```python
import polars as pl
from pathlib import Path
from pdet_data.reader import read_rais

df = read_rais(Path("rais_2023_vinculos.csv"), year=2023, dataset="vinculos")
print(
    df.group_by("cnae_secao")
      .agg(pl.col("id_vinculo").count().alias("empregos"))
      .sort("empregos", descending=True)
)
```

### 2. Evolução do emprego ao longo dos anos

```python
import polars as pl
from pathlib import Path
from pdet_data.reader import read_rais

df = pl.concat([
    read_rais(Path(f"rais_{y}_vinculos.csv"), year=y, dataset="vinculos")
        .with_columns(ano=pl.lit(y))
    for y in range(2019, 2024)
])

evolucao = (
    df.group_by("ano")
      .agg(
          empregos=pl.col("id_vinculo").count(),
          salario_medio=pl.col("vl_remun_medio_nominal").mean(),
      )
      .sort("ano")
)
print(evolucao)
```

### 3. Saldo conjuntural (Novo CAGED, últimos 12 meses)

```python
import polars as pl
from pathlib import Path
from pdet_data.reader import read_caged

arquivos = sorted(Path("dados").glob("cagedmov_*.csv"))[-12:]

df = pl.concat([
    read_caged(f, date=int(f.stem.split("_")[-1]), dataset="caged-2020-mov")
    for f in arquivos
])

saldo = (
    df.with_columns(saldo=pl.col("admissoes") - pl.col("demissoes"))
      .group_by("competencia")
      .agg(saldo_total=pl.col("saldo").sum())
      .sort("competencia")
)
print(saldo)
```

### 4. Diferenças salariais por gênero e setor (RAIS 2023)

```python
import polars as pl
from pathlib import Path
from pdet_data.reader import read_rais

df = read_rais(Path("rais_2023_vinculos.csv"), year=2023, dataset="vinculos")
diferenca = (
    df.group_by(["cnae_secao", "ind_sexo_trabalhador"])
      .agg(
          salario_medio=pl.col("vl_remun_medio_nominal").mean(),
          qtd_pessoas=pl.col("id_vinculo").count(),
      )
      .sort(["cnae_secao", "ind_sexo_trabalhador"])
)
print(diferenca)
```

---

## 🐛 Tratamento de Dados

A ferramenta detecta e corrige automaticamente:

- ✅ **Valores faltantes**: representações listadas em `constants.NA_VALUES`
- ✅ **Formato de números**: remove espaços, ponto separador de milhar, troca vírgula por ponto decimal
- ✅ **Encoding**: `latin-1` (RAIS, CAGED clássico) e `utf-8` (Novo CAGED)
- ✅ **Separador**: detecção automática entre `;`, `\t` e `,`
- ✅ **CSVs ragged**: arquivos listados em `constants.RAGGED_CSV_FILES` são re-escritos truncando linhas para o tamanho do header
- ✅ **Tipos de dados**: INT64, FLOAT64, BOOLEAN, Categorical conforme `INTEGER_COLUMNS`, `NUMERIC_COLUMNS`, `BOOLEAN_COLUMNS`

---

## 📈 Performance

Para arquivos RAIS de um ano (~10 GB descompactado):

| Operação | Tempo aproximado | Memória |
|----------|------------------|---------|
| Download (FTP) | 5–15 min | – |
| Descompactação (7z) | 1–3 min | – |
| Leitura + tipagem | ~10 s | ~2 GB |
| Agregação simples | < 1 s | – |

*Especificações: processador moderno, 16 GB RAM, SSD.*

---

## 📖 Referências

- **PDET**: [pdet.mte.gov.br](http://pdet.mte.gov.br/microdados-rais-e-caged)
- **RAIS**: [Documentação Oficial](http://pdet.mte.gov.br/rais)
- **CAGED**: [Documentação Oficial](http://pdet.mte.gov.br/caged)
- **Novo CAGED (2020+)**: [Documentação Oficial](http://pdet.mte.gov.br/novo-caged)

---

## 📝 Licença

MIT

---

## 👤 Autor

Daniel Komesu ([github](https://github.com/dankkom))
