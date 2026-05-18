---
title: Fundações da Quantilica
description: Os dois pacotes que sustentam todo o ecossistema — infraestrutura de I/O e camada analítica.
---

# Fundações

Cada coletor da Quantilica é especializado para a sua fonte. Mas **todos compartilham as mesmas duas fundações**, que entregam o comportamento técnico comum: rede resiliente, armazenamento atômico, proveniência criptográfica e conversão Parquet tipada.

Essa separação não é cosmética. Ela é a razão pela qual o ecossistema escala sem virar monolito.

## `quantilica-core` — infraestrutura de I/O

Base estável e leve. Sem dependências binárias pesadas.

- `http`/`ftp`: clients resilientes com retry e manifestos.
- `storage`: `LocalStorage` com escrita atômica.
- `manifests`: rastreabilidade SHA-256 (`DownloadManifest`, `DatasetManifest`, `RunManifest`).
- `metadata`: modelos genéricos para catálogos.
- `logging` + `exceptions`: padrões consistentes em toda a stack.

→ [Documentação completa](quantilica-core.md)

## `quantilica-io` — camada analítica

A ponte entre arquivos brutos e ativos analíticos prontos.

- Reader multi-formato: CSV, Excel, DBF, JSON.
- Writer Parquet com Polars + PyArrow, compressão `zstd`.
- Data Contracts: validação de schema na ingestão.
- Proveniência injetada no header do Parquet — time travel real.

→ [Documentação completa](quantilica-io.md)

---

## Por que dois pacotes, não um?

Um cientista de dados que só quer baixar séries do SIDRA não deveria precisar instalar 50 MB de binários do Polars e do Arrow para isso. E uma equipe de engenharia construindo um data lake não deveria ter que reimplementar `to_parquet()` em cada fetcher.

A divisão `core` / `io` deixa cada camada com responsabilidade única:

| Camada | Depende de | Tamanho | Para quem |
|---|---|---|---|
| `quantilica-core` | stdlib + `httpx` | leve | todo coletor, todo usuário |
| `quantilica-io` | core + Polars + PyArrow | pesado | quem processa para análise |

Veja a [Arquitetura do Ecossistema](../concepts/arquitetura.md) para o desenho completo das camadas.

## E o host de CLI?

[`quantilica-cli`](quantilica-cli.md) é o ponto de entrada unificado do ecossistema: descobre fetchers instalados via entry points e os monta como subcomandos. Não é uma fundação no sentido de "todo coletor depende dela" — é um **host** que consome os fetchers. Foi incluído na seção Fundações por afinidade arquitetural (compartilha o mesmo padrão de design domain-neutral).

## `quantilica-cloud` — sincronização com a nuvem

Plugin opt-in que sincroniza os manifestos de download locais com um catálogo na nuvem. Registrado sob `quantilica.commands`, expõe os subcomandos `quantilica cloud login`, `quantilica cloud sync` e `quantilica cloud status`. A coleta de dados nunca depende deste pacote.

→ [Documentação completa](quantilica-cloud.md)

## `quantilica-catalog` — modelo canônico de observações

Resolve o cruzamento multi-fonte: define um star schema comum (`fact_observation` + dimensões de indicador e geográfica) e adaptadores que convertem DataFrames de cada fetcher para esse formato. Torna qualquer `JOIN` entre IBGE, BCB, INMET e demais fontes trivial.

→ [Documentação completa](quantilica-catalog.md)

---

## Visão geral das camadas de infraestrutura

| Camada | Pacote | Depende de | Para quem |
|---|---|---|---|
| I/O resiliente | `quantilica-core` | stdlib + httpx | todo coletor |
| Analítica | `quantilica-io` | core + Polars + PyArrow | quem processa para análise |
| CLI | `quantilica-cli` | core | quem usa a linha de comando |
| Nuvem | `quantilica-cloud` | core + cli (runtime) | quem quer sincronizar manifestos |
| Catálogo | `quantilica-catalog` | io + Polars | quem cruza múltiplas fontes |
