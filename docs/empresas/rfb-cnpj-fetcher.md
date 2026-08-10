---
title: rfb-cnpj-fetcher — Base de CNPJs
description: Downloader resiliente e conversor otimizado para a base de 245 GB de CNPJs da Receita Federal.
---

# `rfb-cnpj-fetcher`

O `rfb-cnpj-fetcher` orquestra o download paralelo, extração e tipagem da base pública de CNPJs da Receita Federal, transformando mais de **245 GB** de dados brutos em Parquet.

## Instalação

```bash
quantilica install rfb-cnpj
```

## Características

- **Download Concorrente:** Baixa os ZIPs do site da Receita Federal explorando a largura de banda máxima disponível.
- **Transformação Direta:** Os arquivos ZIP são lidos sob demanda (streaming) e transformados em Parquet, pulando a necessidade de ocupar dezenas de gigabytes com CSVs intermediários.
- **Merge (Opcional):** Fornece opções para consolidar `Estabelecimentos`, `Empresas` e `Sócios` em um único banco DuckDB para análises imediatas.

## Como Usar

Sincronizando a base inteira:

```bash
quantilica rfb-cnpj sync -o ./data/rfb
```

Aviso: Devido ao tamanho da base (245 GB), certifique-se de que há espaço em disco suficiente no diretório de destino.
