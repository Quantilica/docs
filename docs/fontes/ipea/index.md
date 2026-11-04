---
title: Ipeadata — séries do Ipea
description: Séries macroeconômicas, sociais e regionais do Ipeadata (Ipea), com carga histórica incremental e partições por base, periodicidade e nível.
---

# Ipeadata (Ipea)

## O desafio

O Ipeadata reúne cerca de 4.000 séries de fontes diversas, em periodicidades e níveis territoriais diferentes (uma mesma série pode misturar Municípios, Estados e Brasil). Rebaixar tudo a cada execução é inviável. O `ipeadata-fetcher` guarda a data de atualização de cada série e só recarrega o que mudou.

## Pacotes

| Ferramenta | O que faz |
|---|---|
| **[ipeadata-fetcher](ipeadata-fetcher.md)** | Coleta séries pela API OData, com `backfill` incremental em paralelo, e converte para Parquet particionado por base, periodicidade e nível. |

## Próximos passos

- Para baixar e converter: vá para **[ipeadata-fetcher](ipeadata-fetcher.md)**.
- Antes de rodar um download grande, confira o [estado das fontes](../../status.md).
