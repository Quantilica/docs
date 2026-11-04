---
title: infosiga-fetcher — Sinistros de trânsito de São Paulo
description: Baixa o pacote de dados do Infosiga-SP (sinistros, pessoas e veículos) e converte os CSVs para o lake Hive em Parquet particionado por ano.
---

# `infosiga-fetcher`

O `infosiga-fetcher` baixa os dados abertos do Infosiga-SP (sistema de informações de sinistros de trânsito do Estado de São Paulo, do Detran-SP) e converte os CSVs para o lake Hive em Parquet.

| | |
|---|---|
| **Fonte** | Detran-SP, painel Infosiga (`infosiga.detran.sp.gov.br`) |
| **Formato** | ZIP com CSVs (`;`, cp1252) |
| **Organização** | 2 grupos: `dados` (1 arquivo) e `dicionario` (1 arquivo) |
| **Escopo do pacote** | download e conversão para Parquet. A carga em banco não faz parte dele |

!!! note "Pacote ainda não publicado"

    O pacote está na branch `feat/r1` e ainda não tem release no índice. Os comandos abaixo valem a partir da primeira publicação.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install infosiga --extra analysis

# Ou como biblioteca no seu projeto
uv add 'infosiga-fetcher[analysis]' --index https://index.quantilica.com/simple/
```

O extra `analysis` é necessário para a conversão ao lake.

**Requisitos:** Python 3.12+

## Primeiro dado

```bash
quantilica infosiga sync -o ./data/infosiga
```

## Comandos

| Comando | O que faz |
|---|---|
| `quantilica infosiga list` | Lista os arquivos dos grupos |
| `quantilica infosiga check` | Compara o disco com o remoto, sem baixar |
| `quantilica infosiga sync` | Baixa os grupos pedidos. Padrão de saída: `/data/infosiga` |
| `quantilica infosiga convert <entrada> <lake>` | Converte o acervo bruto para o lake Hive |

## Conjuntos

Os dois grupos têm um arquivo cada: `dados` (`dados_infosiga.zip`) e `dicionario` (`Infosiga_dicionario_dados.zip`). Os aliases `padrao`, `sinistros`, `acidentes` e `transito` apontam para `dados`. Não há conjuntos "listados" além desses: R1 é o catálogo inteiro.

O ZIP de dados traz vários CSVs por tabela (por exemplo, `veiculos_2015-2021` e `veiculos_2022-2024`), que o lake agrupa em 3 datasets: `sinistros`, `pessoas` e `veiculos`.

## Particionamento no lake

Os três datasets são particionados por `ano`:

- `sinistros`, `pessoas`, `veiculos`: o ano vem de `data_sinistro`/`ano_sinistro` por linha; sem essas colunas, do ano inicial da faixa do arquivo (coluna `periodo_arquivo`).
- Linha sem ano válido vai para `ano=__HIVE_DEFAULT_PARTITION__` (quarentena); não há mais ano inventado.
- Cada membro do ZIP é uma origem própria (`composite_file_key`, chave `zip__membro`), lido em streaming, com decodificação cp1252 estrita e colunas lidas como texto.

## Política de frescor

**F3 (`REMOTE_ONLY`)**: a fonte não expõe validadores confiáveis (`ETag`/`Last-Modified`), então o pacote valida o conteúdo em stream e deduplica por `sha256` local. Nessas fontes o `check` indica "download" sempre, o que é verdade: sem validadores, só o conteúdo revela a mudança.

## Limitações conhecidas

- As colunas reais `data_sinistro`/`ano_sinistro` em `pessoas` e `veiculos` ainda não foram verificadas contra um download real; se faltarem, o ano cai na faixa do nome do arquivo.
- A fonte não oferece validadores, então o ZIP pode ser rebaixado a cada execução.

## Reconversão necessária

Se o lake tiver `veiculos` ou `pessoas` convertidos por versão anterior, apague e reconverta (`--force`): antes só o primeiro CSV de cada ZIP entrava, `veiculos` era particionado por `ano_fab` (ano de fabricação) e a falta de ano virava `2015`.

## Saiba mais

- [Changelog do pacote](https://github.com/Quantilica/infosiga-fetcher/blob/main/CHANGELOG.md)
- [Repositório](https://github.com/Quantilica/infosiga-fetcher)
- [Proveniência e manifestos](../../conceitos/proveniencia.md) e [Parquet + Polars](../../conceitos/parquet-polars.md)
