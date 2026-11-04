---
title: antt-fetcher — Dados abertos da ANTT
description: Coleta rodovias, cargas, passageiros, ferrovias e fiscalização do portal de dados abertos da ANTT e converte para o lake Hive em Parquet.
---

# `antt-fetcher`

O `antt-fetcher` coleta os dados abertos da ANTT (Agência Nacional de Transportes Terrestres) publicados no portal CKAN e no gov.br, e converte os CSVs para o lake Hive em Parquet.

| | |
|---|---|
| **Fonte** | ANTT, portal de dados abertos (CKAN) e uma planilha XLSX no gov.br |
| **Formato** | CSV (preferido) e JSON; XLSX no grupo `govbr` |
| **Organização** | 9 grupos, 106 pacotes do CKAN mais o XLSX do gov.br, e 3 macro-aliases |
| **Escopo do pacote** | download e conversão para Parquet. A carga em banco não faz parte dele |

!!! note "Pacote ainda não publicado"

    O pacote está na branch `feat/r1` e ainda não tem release no índice. Os comandos abaixo valem a partir da primeira publicação.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install antt --extra analysis

# Ou como biblioteca no seu projeto
uv add 'antt-fetcher[analysis]' --index https://index.quantilica.com/simple/
```

O extra `analysis` é necessário para a conversão ao lake.

**Requisitos:** Python 3.12+

## Primeiro dado

```bash
quantilica antt list
quantilica antt sync -o ./data/antt
```

## Comandos

| Comando | O que faz |
|---|---|
| `quantilica antt list` | Lista os arquivos dos pacotes R1 |
| `quantilica antt catalogo [grupo] [--tier]` | Catálogo completo (R1 e listados), sem rede |
| `quantilica antt discover [--json] [--fail-on-change]` | Aponta pacotes novos, removidos na fonte (o bruto é mantido) e crescidos. Resposta vazia ou do WAF vira erro, nunca "tudo removido" |
| `quantilica antt check` | Compara o disco com o remoto, sem baixar |
| `quantilica antt sync` | Baixa os grupos pedidos. Padrão de saída: `/data/antt` |
| `quantilica antt convert <entrada> <lake>` | Converte o acervo bruto para o lake Hive |

## Conjuntos: R1 e listados

O CKAN da ANTT publicava 106 pacotes em 2026-11-03; o catálogo cobre os 106 mais o XLSX do gov.br.

| Grupo | Pacotes | R1 (baixa) | Listado |
|---|---:|---:|---:|
| rodovias | 53 | 11 | 42 |
| cargas | 10 | 3 | 7 |
| passageiros | 22 | 14 | 8 |
| ferrovias | 6 | 2 | 4 |
| fiscalizacao | 8 | 5 | 3 |
| ouvidoria | 2 | 0 | 2 |
| tecnologia | 2 | 0 | 2 |
| visualizacoes | 3 | 0 | 3 |
| govbr | 1 | 1 | 0 |

`list` e `sync` operam só no tier R1: **35 pacotes do CKAN mais o XLSX do gov.br**. Os demais estão listados. Quatro pacotes não têm CSV nem JSON (só PDF, KMZ ou painel) e nunca baixam. Macro-aliases: `infraestrutura`, `transporte-rodoviario` e `gestao`.

O grupo `govbr` traz a produção ferroviária origem-destino (XLSX de cerca de 9 MB). O nome do arquivo muda a cada mês, então a URL é resolvida pela página; o gov.br recusa HEAD (403), mas aceita GET com `Range`.

## Particionamento no lake

O lake converte **5 conjuntos** (`volume-trafego-praca-pedagio`, `acidentes-rodovias`, `rntrc`, `monitriip-servico-regular-paradas` e `relatorio-acompanhamento-acidentes-ferroviarios-raaf`), particionados por `ano`. O ano vem de cada linha (coluna de data do conjunto), então um CSV multi-ano gera uma partição por ano. O `rntrc` (retrato mensal) usa o período declarado no nome do arquivo. Linha sem ano válido vai para `ano=__HIVE_DEFAULT_PARTITION__`, com aviso. Os demais pacotes R1 ficam como bruto, sem conversão.

Cada membro de ZIP é uma origem própria (`composite_file_key`), com leitura em streaming.

## Política de frescor

**F2 (`HEAD_FALLBACK_GET`)**: HEAD com `ETag`/`Last-Modified`/`Content-Length`, com fallback para `GET` com `Range: bytes=0-0` quando o servidor devolve 403/405 ou não envia cabeçalhos.

## Limitações conhecidas

- O portal fica atrás de um WAF (F5). Respostas "Request Rejected" são tratadas como falha transitória, nunca como arquivo.
- O lake converte só os 5 conjuntos originais; o restante do R1 fica como bruto.
- Pacote removido do CKAN não derruba mais o grupo inteiro no `list`.

## Reconversão necessária

Reconverta com `--force` qualquer conjunto já convertido por versão anterior: o ano da partição era o da primeira linha do arquivo (com `2024` como fallback silencioso) e os ZIPs com vários membros só entregavam o primeiro.

## Saiba mais

- [Changelog do pacote](https://github.com/Quantilica/antt-fetcher/blob/main/CHANGELOG.md)
- [Repositório](https://github.com/Quantilica/antt-fetcher)
- [Proveniência e manifestos](../../conceitos/proveniencia.md) e [Parquet + Polars](../../conceitos/parquet-polars.md)
