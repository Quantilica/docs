---
title: inep-fetcher — Microdados do INEP
description: Downloader e conversor para os microdados massivos do INEP (Censo Escolar e ENEM).
---

# `inep-fetcher`

O `inep-fetcher` é a ferramenta dedicada para coletar, unificar e converter os mais de **39 GB** de microdados divulgados pelo INEP.

## Instalação

```bash
quantilica install inep
```

## Características

- **Streaming Chunked:** Evita estouro de memória ao processar CSVs de mais de 5 GB.
- **Conversão automática:** Transforma tudo em Parquet tipado.
- **Unificação de dicionários:** Padroniza encodings e delimitadores problemáticos.

## Como Usar

Baixando os microdados do ENEM (um grupo do catálogo; `quantilica inep list` mostra todos):

```bash
quantilica inep sync enem -o ./data/inep
```

Os arquivos são baixados no formato de origem (ZIP).
