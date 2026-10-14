---
title: Mercado de Trabalho — CAGED e RAIS
description: Microdados de emprego formal (CAGED, RAIS) processados com Polars sem estourar memória — pdet-fetcher.
---

# Mercado de Trabalho

Seu notebook abre o CSV da RAIS — só o arquivo de São Paulo em 2024 tem 24,6 milhões de linhas e 6,6 GB — e o Pandas morre antes do primeiro `groupby`. Esse é o batismo de quem estuda emprego formal no Brasil: os microdados administrativos do Ministério do Trabalho são um censo do país inteiro, e cobram pedágio em memória de quem chega despreparado. Duas fontes, dois ritmos:

- **RAIS** (Relação Anual de Informações Sociais) — censo anual de todas as relações de emprego formal. Série de 1985 até hoje. Em 2024 são 6 arquivos: 3,4 GiB compactados, 87,7 milhões de vínculos e 22,0 GiB (23,6 GB) de CSV.
- **CAGED** (Cadastro Geral de Empregados e Desempregados) — registro mensal de fluxos (admissões e desligamentos) por setor/região. O Novo CAGED (desde 2020) tem cerca de 465 MB de CSV por mês de movimentações (ago/2026: 4,4 milhões de linhas, 51 MB compactados); o CAGED antigo vai de 2007 a 2019, com arquivos de ajustes desde 2002.

## O desafio

- **Esgotamento de memória** — a RAIS de 2024 tem 87,7 milhões de linhas (24,6 milhões só em SP), o que pede leitura lazy, filtro cedo e Parquet.
- **Ineficiência de formato** — CSV/TXT legados são lentos, não-tipados e desperdiçam espaço (CSV: 8 GB; Parquet equivalente: 0.4 GB).
- **Explosão de arquivos temporários** — descompressão `.7z` exige espaço em disco frequentemente indisponível em VMs cloud.
- **Esquema variável** — colunas e tipos mudam ao longo dos anos (década de 1990 vs. 2020 são quase incompatíveis).

## Dois stacks: Exploração vs. Produção

### Stack 1 — Exploração (Parquet ad-hoc + Polars)

Para análise pontual de um ou poucos anos. Após uma conversão inicial dos brutos para Parquet, todo o trabalho subsequente acontece direto em Polars/Jupyter.

```mermaid
graph LR
    A[FTP MTE] --> B[quantilica pdet sync<br/>raw .7z]
    B --> C[quantilica pdet convert<br/>→ Parquet]
    C --> D[Polars / Jupyter<br/>análise ad-hoc]
```

### Stack 2 — Produção (Pipeline `pdet-fetcher` agendado)

Para pipelines diários/mensais que produzem artefatos versionados. RAIS é anual (release dezembro do ano seguinte); CAGED é mensal com 3 semanas de atraso. Agende `quantilica pdet pipeline` (sync → convert) para rodar quando novos arquivos saem; resultados são idempotentes (re-rodar não custa nada).

```mermaid
graph LR
    A[FTP MTE] --> B[scheduler<br/>cron / Airflow]
    B --> C[quantilica pdet pipeline]
    C --> D[Parquet versionado]
    D --> E[(PostgreSQL<br/>opcional)]
    E --> F[BI / dashboards]
```

## Pacotes

- **[pdet-fetcher](pdet-fetcher.md)** — engine de transformação Big Data. Fetch FTP idempotente, descompressão `.7z`, parser CSV com schema por-ano, escrita Parquet via Polars. Throughput: 50M linhas → Parquet em ~60s; cache de re-runs em ~0.08s.

Para o tutorial de Parquet + Polars (não específico de RAIS, aplicável a qualquer dataset grande), veja **[Parquet + Polars](../concepts/parquet-polars.md)** em Conceitos.

Os [Princípios de Design](../concepts/principios.md) do ecossistema — especialmente Performance e Sem Mágica — são centrais aqui: leitura de CSV com Polars 14× a 22× mais rápida que o pandas nos arquivos medidos, conversão determinística, sem caching escondido. Receitas táticas em [Padrões Práticos](../concepts/padroes.md): [Parquet vs. CSV](../concepts/padroes.md#parquet-vs-csv), [Lazy evaluation](../concepts/padroes.md#lazy-evaluation), [Memória para arquivos grandes](../concepts/padroes.md#memoria-arquivos-grandes).

## Estrutura de dados

### Campos RAIS (seleção)

| Campo | Tipo | Descrição |
|---|---|---|
| `year` | int | Ano de competência |
| `employee_id` | str | ID anônimo de funcionário |
| `employer_id` | str | CNPJ/ID da firma |
| `state` | str | UF |
| `cnae_code` | str | Setor econômico |
| `occupation_code` | str | CBO |
| `salary` | float | Salário mensal (R$) |
| `tenure_days` | int | Permanência no emprego |

### Campos CAGED (seleção)

| Campo | Tipo | Descrição |
|---|---|---|
| `year_month` | date | Ano-mês de competência |
| `state` | str | UF |
| `cnae_code` | str | Setor econômico |
| `admissions` | int | Contratações no mês |
| `demissions` | int | Desligamentos no mês |
| `net_flow` | int | Saldo (admissions − demissions) |

## Próximos passos

- Para começar a converter RAIS/CAGED: vá para **[pdet-fetcher](pdet-fetcher.md)**.
- Para o tutorial de Parquet+Polars: veja **[Parquet + Polars](../concepts/parquet-polars.md)**.
- Para combinar emprego com PIB e yields do Tesouro: veja **[Análise Econômica Multi-Fonte](../cookbook/analise-economica-multi-fonte.md)**.

## Recursos externos

- [RAIS (oficial)](https://www.gov.br/trabalho/pt-br/acesso-a-informacao/dados-abertos/rais)
- [CAGED (oficial)](https://www.gov.br/trabalho/pt-br/acesso-a-informacao/dados-abertos/caged)
