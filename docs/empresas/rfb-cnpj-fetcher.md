---
title: rfb-cnpj-fetcher — Base de CNPJs
description: Downloader dos ZIPs da base pública de CNPJs da Receita Federal.
---

# `rfb-cnpj-fetcher`

O `rfb-cnpj-fetcher` baixa, em paralelo, os ZIPs da base pública de CNPJs da Receita Federal (37 arquivos: cerca de **7,8 GB** em ZIP e **28,7 GB** descompactados, medidos na referência de setembro de 2026). O pacote só baixa: não extrai os ZIPs nem converte os dados.

## Instalação

```bash
quantilica install rfb-cnpj
```

## Características

- **Download concorrente:** baixa os ZIPs do site da Receita Federal em paralelo (`--workers`).
- **Frescor:** `sync` pula os ZIPs locais que já estão atualizados, e `check` mostra o plano antes de baixar.
- **Manifestos SHA-256:** cada download grava um manifesto de proveniência.
- **Fora do pacote:** a extração dos ZIPs e a conversão para Parquet ou DuckDB não fazem parte do `rfb-cnpj-fetcher`.

## Como Usar

Sincronizando a base inteira:

```bash
quantilica rfb-cnpj sync -o ./data/rfb
```

Aviso: a base ocupa cerca de 8 GB em ZIP (29 GB depois de extraída); certifique-se de que há espaço em disco suficiente no diretório de destino.
