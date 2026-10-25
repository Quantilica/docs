---
title: quantilica-sql — Motor SQL unificado
description: Carrega dados das fontes públicas em PostgreSQL com cargas idempotentes e materializa pipelines analíticos. Substitui sidra-sql e bcb-sgs-sql.
---

# `quantilica-sql`

O `quantilica-sql` é o motor SQL do ecossistema. Ele carrega os arquivos baixados pelos coletores em schemas dedicados do PostgreSQL, sem repetir cargas já feitas, e executa pipelines declarativos que materializam tabelas e views na camada `analytics`.

Ele **substitui** os motores `sidra-sql` e `bcb-sgs-sql`, que seguem documentados e funcionando enquanto você migra. Os pipelines vêm do catálogo [`quantilica-pipelines`](quantilica-pipelines.md).

| | |
|---|---|
| **Versão** | 0.1.1 |
| **Banco** | PostgreSQL (driver `psycopg` 3, carga por `COPY`) |
| **Fontes** | 15 adaptadores: ANAC, ANP, B3, BCB-SGS, Comex, CVM, DATASUS, INEP, INMET, PDET, RFB-CNPJ, RTN, SIDRA, Tesouro Direto e TSE |
| **Distribuição** | índice da Quantilica (não está no PyPI) |

!!! note "Escopo"

    O `quantilica-sql` **não baixa** dados. Baixe com o coletor da fonte (`quantilica <fonte> sync`) e aponte a carga para o diretório baixado. A separação mantém os coletores leves e a carga em banco opcional.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install sql

# Ou como biblioteca no seu projeto
uv add quantilica-sql --index https://index.quantilica.com/simple/
```

O extra `analysis` (Polars e PyArrow) só é necessário para a carga de alguns arquivos grandes, como os ZIPs da RFB-CNPJ:

```bash
uv add 'quantilica-sql[analysis]' --index https://index.quantilica.com/simple/
```

**Requisitos:** Python 3.12+ e um PostgreSQL acessível.

## Configuração

A conexão vem da variável de ambiente `DATABASE_URL`. Sem ela, o padrão é `postgresql://postgres@localhost:5432/dados`.

```bash
export DATABASE_URL='postgresql://<usuario>:<senha>@localhost:5432/dados'
```

Outras variáveis: `QUANTILICA_STORAGE_ROOT` (raiz dos dados baixados, padrão `./data`) e `QUANTILICA_STAGING_DIR` (diretório para staging de arquivos grandes, padrão o diretório temporário do sistema).

## Primeiro uso

```bash
# 1. Baixar com o coletor
quantilica cvm sync cia-cad -o ./data/cvm

# 2. Carregar no PostgreSQL
quantilica sql load cvm -s ./data/cvm

# 3. Ver o que foi carregado
quantilica sql status
```

Rodar o `load` de novo não duplica nada: cada arquivo carregado fica registrado em `{schema}.arquivo_carregado`, e os já registrados são pulados. `--force` refaz a carga.

## Comandos

| Comando | O que faz |
|---|---|
| `quantilica sql status` | Mostra schemas, tamanhos e tabelas no PostgreSQL |
| `quantilica sql load <domínio>` | Carrega uma fonte. `-s` caminho dos arquivos, `-c` competência (`AAAA-MM` ou lista), `-a` todas as partições, `-t` filtra tabela ou grupo, `--tablespace`, `--staging-dir`, `-f` força recarga |
| `quantilica sql run <pipeline>` | Executa um pipeline de transformação na camada `analytics`. `--raw-schema` e `--target-schema` ajustam os schemas |
| `quantilica sql scaffold <nome>` | Gera o esqueleto de um pipeline (`-t ibge`, `bcb` ou `general`) ou de um catálogo (`--catalog`) |
| `quantilica sql plugin install\|list\|remove` | Gerencia catálogos de pipelines instalados via Git |
| `quantilica sql tablespaces` | Lista as tablespaces da instância |
| `quantilica sql maintenance` | Tarefas de manutenção e índices |

Domínios aceitos em `load`: `anac`, `anp`, `b3`, `bcb`, `bcb-sgs`, `comex`, `cvm`, `datasus`, `inep`, `inmet`, `pdet`, `rfb`, `rfb-cnpj`, `rtn`, `secex-comex`, `sidra`, `tddata`, `tesouro-direto`, `tesouro_direto` e `tse`.

Fora da CLI unificada, o mesmo conjunto de comandos está disponível como `quantilica-sql` (útil em scripts, agendadores e contêineres).

## Como funciona

- **Um schema por fonte:** `anp`, `bcb_sgs`, `cvm`, `inmet`, `pdet`, `rfb_cnpj`, `ibge_sidra` e assim por diante.
- **Camada analítica:** o schema `analytics` guarda as tabelas e views produzidas pelos pipelines.
- **Cargas idempotentes:** `{schema}.arquivo_carregado` registra o que já entrou. Rodar duas vezes é seguro.
- **`COPY` em streaming:** a carga usa `COPY` com `psycopg` 3, sem montar o arquivo inteiro em memória.
- **Partições:** tabelas grandes são particionadas por mês ou por ano.
- **Adaptadores:** cada fonte tem um adaptador que sabe localizar os arquivos, criar as tabelas e carregar. Um motor genérico cobre o que é comum entre eles.

## Pipelines

Um pipeline é uma pasta com `fetch.toml` (quais dados brutos usa), `transform.toml` (tabelas de saída, estratégia e chave primária) e um ou mais arquivos `.sql`. Instale o catálogo oficial como plugin e execute:

```bash
quantilica sql plugin install https://github.com/Quantilica/quantilica-pipelines.git --alias std
quantilica sql run macro/juros
```

Veja [`quantilica-pipelines`](quantilica-pipelines.md) para a estrutura e o catálogo.

## Migrando de `sidra-sql` e `bcb-sgs-sql`

| Legado | `quantilica-sql` |
|---|---|
| `sidra-sql run <catálogo> <pipeline>`, `bcb-sgs-sql run …` | `quantilica sql run <pipeline>` (por exemplo `macro/juros`) |
| `bcb-sgs-sql load …` | `quantilica sql load bcb-sgs …` |
| `sidra-sql plugin install\|list\|remove` | `quantilica sql plugin install\|list\|remove` |
| `sidra-sql plugin scaffold` | `quantilica sql scaffold` |
| `config set\|get\|list`, `plugin update`, `plugin validate`, `plugin add-pipeline`, `transform`, `run-path` | sem equivalente na CLI da versão 0.1.1 (a configuração vem de variáveis de ambiente) |

A migração é gradual: os pacotes legados continuam instaláveis e documentados em [sidra-sql](../fontes/ibge/sidra-sql.md) e [bcb-sgs-sql](../fontes/bcb/bcb-sgs-sql.md).

## Saiba mais

- [Changelog do pacote](https://github.com/Quantilica/quantilica-sql/blob/main/CHANGELOG.md)
- [Repositório](https://github.com/Quantilica/quantilica-sql)
- [Bulk load e versionamento](../conceitos/bulk-load.md) e [convenções de armazenamento](../conceitos/storage.md)
