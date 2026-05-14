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
- `manifests`: rastreabilidade SHA-256 (`DownloadManifest`, `ExecutionManifest`).
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
