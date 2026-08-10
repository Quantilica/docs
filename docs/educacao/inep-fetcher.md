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

Baixando o Censo Escolar para um ano específico:

```bash
quantilica inep censo-escolar --ano 2022 -o ./data/inep
```

O download é salvo diretamente em `.parquet`, garantindo compressão e leitura rápida.
