---
title: Balança comercial em uma query DuckDB
description: comex-fetcher baixa os GBs do Siscomex, salva como Parquet, e DuckDB consulta direto sem carregar nada na memória.
---

# Balança comercial em uma query DuckDB

> **Tempo estimado:** 10 minutos (incluindo o primeiro download). **Pacotes:** `comex-fetcher`, `duckdb`.

Dados de comércio exterior do Brasil são **grandes**. Cada arquivo anual do Siscomex em granularidade NCM-8 passa de 1 GB. A receita aqui mostra como combinar dois superpoderes: o coletor resiliente que lida com o servidor governamental, e o DuckDB lendo Parquet direto do disco para consultar bilhões de linhas em segundos.

## O que você vai ver

A balança comercial mensal do Brasil — exportações menos importações — calculada sobre o conjunto completo de transações, sem carregar nada em memória.

## Setup

```bash
uv add "comex-fetcher @ git+https://github.com/Quantilica/comex-fetcher.git" duckdb
```

## A receita

### 1. Baixar e converter para Parquet

```bash
# Importações e exportações dos últimos 5 anos (+ tabelas de códigos)
comex-fetcher sync 2020:2024 -o ./dados
```

Você fica com algo como:

```
parquet/
├── imp_2020.parquet
├── imp_2021.parquet
├── ...
├── exp_2024.parquet
└── codigos/
    ├── pais.parquet
    ├── ncm.parquet
    └── ...
```

### 2. Consultar com DuckDB

```python
import duckdb

con = duckdb.connect()

balanca = con.execute("""
    WITH exportacoes AS (
        SELECT
            CAST(strftime(CAST(printf('%04d-%02d-01', co_ano, co_mes) AS DATE), '%Y-%m') AS DATE) AS mes,
            SUM(vl_fob) AS exportacao
        FROM read_parquet('parquet/exp_*.parquet')
        GROUP BY co_ano, co_mes
    ),
    importacoes AS (
        SELECT
            CAST(strftime(CAST(printf('%04d-%02d-01', co_ano, co_mes) AS DATE), '%Y-%m') AS DATE) AS mes,
            SUM(vl_fob) AS importacao
        FROM read_parquet('parquet/imp_*.parquet')
        GROUP BY co_ano, co_mes
    )
    SELECT
        e.mes,
        e.exportacao,
        i.importacao,
        e.exportacao - i.importacao AS saldo
    FROM exportacoes e
    JOIN importacoes i USING (mes)
    ORDER BY e.mes
""").pl()

print(balanca.tail(12))
```

## O que está acontecendo

- **Sem carregar em memória.** O DuckDB faz *predicate pushdown* no Parquet — lê só as colunas e linhas necessárias. Mesmo com 20 GB no disco, a query usa menos de 1 GB de RAM.
- **Glob no `read_parquet`.** `'parquet/exp_*.parquet'` agrega todos os anos automaticamente. Tipos são unificados pelo DuckDB.
- **`.pl()` no fim.** Materializa o resultado final em Polars para uso posterior — só o que coube no `SELECT` final fica em memória.

## Pegadinhas

- **`co_ano` e `co_mes` são inteiros, não datas.** O Siscomex publica em colunas separadas; o `printf` + `CAST AS DATE` reconstrói.
- **`vl_fob` está em USD.** Para balança em reais, junte com a cotação cambial (BCB SGS 1 ou `tesouro-direto-fetcher`) — mas para evolução, USD é o padrão internacional.
- **Mês corrente é parcial.** O Siscomex publica mês fechado por volta do dia 15 do mês seguinte. Filtre `co_mes` para evitar séries com o último ponto incompleto.
- **NCM mudou.** O sistema NCM 8 cobre 1997+. Pré-1997 (NBM) tem schema diferente — não tente unir os dois Parquets.

## Variações

- **Top 10 produtos exportados** — `GROUP BY co_ncm`, join com `codigos/ncm.parquet` para nomes.
- **Concentração geográfica** — `GROUP BY co_pais`, join com `codigos/pais.parquet`.
- **Análise por estado** — `GROUP BY sg_uf_ncm` em vez de mês.
- **Saldo bilateral com a China** — filtre `co_pais = '160'` (China) e plote.

## Veja também

- [comex-fetcher](../comex/comex-fetcher.md)
- [Parquet + Polars](../concepts/parquet-polars.md)
- [Princípios — Performance](../concepts/principios.md#performance)
