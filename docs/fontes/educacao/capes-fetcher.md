---
title: capes-fetcher — Dados abertos da CAPES
description: Coleta teses, programas e cursos de pós-graduação do portal de dados abertos da CAPES (CKAN) e converte os CSVs para o lake Hive em Parquet.
---

# `capes-fetcher`

O `capes-fetcher` coleta os dados abertos da CAPES (pós-graduação stricto sensu) publicados no portal CKAN e converte os CSVs para o lake Hive em Parquet.

| | |
|---|---|
| **Fonte** | CAPES, portal de dados abertos (CKAN) |
| **Formato** | CSV (XLSX, RDF e TTL nunca são baixados: o XLSX duplica o CSV) |
| **Organização** | 11 grupos, 89 pacotes catalogados e 3 macro-aliases |
| **Escopo do pacote** | download e conversão para Parquet. A carga em banco não faz parte dele |

!!! note "Pacote ainda não publicado"

    O pacote está na branch `feat/r1` e ainda não tem release no índice. Os comandos abaixo valem a partir da primeira publicação.

!!! warning "Servidor lento"

    O servidor da CAPES é muito lento: em 2026-11-03, `package_list` levou cerca de 130 s e `package_search` com 100 pacotes cerca de 250 s. Os comandos que consultam o CKAN (`list`, `sync`, `discover`) podem demorar.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install capes --extra analysis

# Ou como biblioteca no seu projeto
uv add 'capes-fetcher[analysis]' --index https://index.quantilica.com/simple/
```

O extra `analysis` é necessário para a conversão ao lake.

**Requisitos:** Python 3.12+

## Primeiro dado

```bash
quantilica capes sync teses -o ./data/capes
```

## Comandos

| Comando | O que faz |
|---|---|
| `quantilica capes list` | Lista os arquivos dos pacotes R1 |
| `quantilica capes catalogo [grupo] [--tier]` | Catálogo completo (R1 e listados), sem rede |
| `quantilica capes discover [--json] [--fail-on-change]` | Consulta o `package_list` do CKAN e aponta pacotes novos (era nova de um tema) ou removidos. Resposta vazia vira erro, nunca "tudo removido" |
| `quantilica capes check` | Compara o disco com o remoto, sem baixar |
| `quantilica capes sync` | Baixa os grupos pedidos, um recurso por ano. Padrão de saída: `/data/capes` |
| `quantilica capes convert <entrada> <lake>` | Converte o acervo bruto para o lake Hive |

## Conjuntos: R1 e listados

O CKAN publicava 89 pacotes em 2026-11-03, fatias por era de 26 temas. O catálogo cobre os 89.

| Grupo | Temas | Pacotes | R1 (baixa) | Listado |
|---|---:|---:|---:|---:|
| teses | 1 | 4 | 4 | 0 |
| programas | 1 | 3 | 3 | 0 |
| cursos | 1 | 3 | 3 | 0 |
| pessoas | 2 | 8 | 0 | 8 |
| producao | 3 | 16 | 0 | 16 |
| projetos | 3 | 11 | 0 | 11 |
| bolsas | 5 | 17 | 0 | 17 |
| formacao-professores | 4 | 8 | 0 | 8 |
| fomento | 3 | 9 | 0 | 9 |
| periodicos | 1 | 5 | 0 | 5 |
| gestao | 2 | 5 | 0 | 5 |

`list` e `sync` operam só nos **10 pacotes R1** (teses, programas, cursos). Os outros 79 ficam listados. Macro-aliases: `pos-graduacao`, `bolsas-e-fomento` e `institucional`.

## Particionamento no lake

O lake converte os 3 conjuntos R1 (`teses`, `programas`, `cursos`), particionados por `ano`. O ano vem de cada linha (`ano_base`), então um CSV com vários anos gera uma partição por ano. Linha sem ano válido vai para `ano=__HIVE_DEFAULT_PARTITION__`, com aviso de contagem. Sem `ano_base`, só um ano único declarado no nome do arquivo é aceito; caso contrário o arquivo vira erro.

Cada membro de ZIP é uma origem própria (`composite_file_key`), a leitura é em streaming e as colunas são lidas como texto.

## Política de frescor

**F2 (`HEAD_FALLBACK_GET`)**: HEAD com `ETag`/`Last-Modified`/`Content-Length`; se o servidor responder 403/405 ou sem cabeçalhos, usa `GET` com `Range: bytes=0-0`.

## Limitações conhecidas

- O catálogo web de teses (`catalogodeteses.capes.gov.br`, POST, 20 por página) fica fora do fetcher: não serve para coleta em massa.
- O `discover` consulta só o `package_list`, por causa da lentidão do servidor.
- 79 pacotes estão apenas catalogados, sem download.

## Reconversão necessária

Se o lake tiver `teses`, `programas` ou `cursos` convertidos por versão anterior, vale reconverter com `--force`: antes o ano da partição era o da primeira linha do arquivo, e linhas sem ano recebiam `2024` em silêncio.

## Saiba mais

- [Changelog do pacote](https://github.com/Quantilica/capes-fetcher/blob/main/CHANGELOG.md)
- [Repositório](https://github.com/Quantilica/capes-fetcher)
- [Proveniência e manifestos](../../conceitos/proveniencia.md) e [Parquet + Polars](../../conceitos/parquet-polars.md)
