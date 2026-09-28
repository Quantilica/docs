---
title: Fundações da Quantilica
description: A base técnica compartilhada por todo o ecossistema — I/O resiliente, camada analítica, CLI unificada e catálogo canônico.
---

# Fundações

Cada coletor da Quantilica é especializado para a sua fonte. Mas **todos compartilham a mesma base técnica**, que entrega o comportamento comum: rede resiliente, armazenamento atômico, proveniência criptográfica, conversão Parquet tipada, CLI unificada e modelo canônico de observações.

Essa separação não é cosmética. Ela é a razão pela qual o ecossistema escala sem virar monolito.

## `quantilica-core` — infraestrutura de I/O

Base estável e leve. Sem dependências binárias pesadas.

- `http`/`ftp`: clients resilientes com retry e manifestos.
- `storage`: `LocalStorage` com escrita atômica.
- `manifests`: rastreabilidade SHA-256 (`DownloadManifest`, `DatasetManifest`, `RunManifest`).
- `metadata`: modelos genéricos para catálogos.
- `logging` + `exceptions`: padrões consistentes em toda a stack.

→ [Documentação completa](quantilica-core.md)

## `quantilica-analytics` — camada analítica

A ponte entre arquivos brutos e ativos analíticos prontos.

- Reader multi-formato: CSV, Excel, DBF, JSON.
- Writer Parquet com Polars + PyArrow, compressão `zstd`.
- Data Contracts: validação de schema na ingestão.
- Proveniência injetada no header do Parquet — time travel real.

→ [Documentação completa](quantilica-analytics.md)

---

## Por que dois pacotes, não um?

Um cientista de dados que só quer baixar séries do SIDRA não deveria precisar instalar 50 MB de binários do Polars e do Arrow para isso. E uma equipe de engenharia construindo um data lake não deveria ter que reimplementar `to_parquet()` em cada fetcher.

Por isso a base é dividida em camadas — `core` (I/O leve) e `analytics` (processamento pesado com Polars/PyArrow) — cada uma com responsabilidade única, sem desperdício de dependências. O host de CLI e o catálogo canônico completam a base sem acoplamento.

Veja o desenho completo na [Arquitetura do Ecossistema](../concepts/arquitetura.md).

## E o host de CLI?

[`quantilica-cli`](quantilica-cli.md) é o ponto de entrada unificado do ecossistema: descobre fetchers instalados via entry points e os monta como subcomandos. Não é uma fundação no sentido de "todo coletor depende dela" — é um **host** que consome os fetchers. Foi incluído na seção Fundações por afinidade arquitetural (compartilha o mesmo padrão de design domain-neutral).

## `quantilica-catalog` — modelo canônico de observações

Resolve o cruzamento multi-fonte: define um star schema comum (`fact_observation` + dimensões de indicador e geográfica) e adaptadores que convertem DataFrames de cada fetcher para esse formato. Torna qualquer `JOIN` entre IBGE, BCB, INMET e demais fontes trivial.

→ [Documentação completa](quantilica-catalog.md)

---

## Visão geral das camadas de infraestrutura

| Camada | Pacote | Depende de | Tamanho | Para quem |
|---|---|---|---|---|
| I/O resiliente | `quantilica-core` | stdlib + httpx2 | Leve | Todo coletor, todo usuário |
| Analítica | `quantilica-analytics` | core + Polars + PyArrow | Pesado | Quem processa dados para análise |
| CLI unificada | `quantilica-cli` | core | Leve | Quem interage via linha de comando |
| Catálogo unificado | `quantilica-catalog` | io + Polars | Pesado | Quem cruza dados de múltiplas fontes |
