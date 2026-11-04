---
title: pgfn-fetcher — Dívida ativa da União (PGFN)
description: Baixa os arquivos trimestrais de dívida ativa da PGFN (SIDA, previdenciária e FGTS) e converte os CSVs para o lake Hive em Parquet por ano e trimestre.
---

# `pgfn-fetcher`

O `pgfn-fetcher` baixa os arquivos trimestrais de dívida ativa da União publicados pela PGFN (Procuradoria-Geral da Fazenda Nacional) e converte os CSVs para o lake Hive em Parquet.

| | |
|---|---|
| **Fonte** | PGFN, dados abertos (`dadosabertos.pgfn.gov.br`) |
| **Formato** | ZIP trimestral com vários CSVs |
| **Organização** | 3 grupos: `sida`, `previdenciario` e `fgts`, um arquivo por trimestre desde 2020 |
| **Escopo do pacote** | download e conversão para Parquet. A carga em banco não faz parte dele |

!!! note "Pacote ainda não publicado"

    O pacote está na branch `feat/r1` e ainda não tem release no índice. Os comandos abaixo valem a partir da primeira publicação.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install pgfn --extra analysis

# Ou como biblioteca no seu projeto
uv add 'pgfn-fetcher[analysis]' --index https://index.quantilica.com/simple/
```

O extra `analysis` é necessário para a conversão ao lake.

**Requisitos:** Python 3.12+

## Primeiro dado

```bash
quantilica pgfn sync sida -o ./data/pgfn
```

## Comandos

| Comando | O que faz |
|---|---|
| `quantilica pgfn list` | Lista os arquivos dos grupos, a partir da listagem real de cada trimestre |
| `quantilica pgfn check` | Compara o disco com o remoto, sem baixar |
| `quantilica pgfn sync` | Baixa os grupos pedidos. Padrão de saída: `/data/pgfn` |
| `quantilica pgfn convert <entrada> <lake>` | Converte o acervo bruto para o lake Hive |

## Conjuntos

| Grupo | O que é | Encoding |
|---|---|---|
| `sida` | Dívida ativa não previdenciária (SIDA) | cp1252 |
| `previdenciario` | Dívida ativa previdenciária | UTF-8 |
| `fgts` | Dívida ativa do FGTS | cp1252 |

Aliases: `padrao`, `nao_previdenciario`, `dau` e `tributaria` apontam para `sida`; `prev`, para `previdenciario`. São 3 conjuntos, todos baixados e convertidos (não há conjuntos apenas listados).

O catálogo é dirigido pela listagem real de cada trimestre: os nomes dos arquivos variam (por exemplo `Nao_Previdenciariozip.zip` em 2022-T4 e `Sistema_SIDA.zip` em 2026-T3). Se a listagem de um trimestre falhar, usa o nome fixo; arquivo esperado e ausente não vira entrada (sem 404 diário) e é contado em `DiscoveryReport.missing`. O catálogo para no último trimestre fechado.

## Particionamento no lake

Os três datasets são particionados por `ano` e `trimestre`. Cada membro do ZIP é uma origem própria (`composite_file_key`, chave `zip__membro`) e é lido em streaming, sem carregar o membro inteiro em memória. A decodificação é estrita (sem `errors="replace"`): byte inválido vira erro contado. Colunas são lidas como texto, para que o CNPJ com zero à esquerda não vire inteiro. Período não inferido do nome do arquivo é erro, não mais `2020-T1`.

Em `sida` 2026-T3 o `CPF_CNPJ` vem formatado (`84.461.748/0001-81`); o `cnpj_basico` extrai os 14 dígitos.

## Política de frescor

**F2 (`HEAD_FALLBACK_GET`)**: HEAD com `ETag`/`Last-Modified`/`Content-Length`, com fallback para `GET` com `Range: bytes=0-0` quando o servidor devolve 403/405 ou não envia cabeçalhos.

## Limitações conhecidas

- `PGFN_DISCOVER=0` desliga a descoberta (usado em testes offline).
- Os ZIPs são grandes; a leitura em streaming evita carregar o membro inteiro em memória.

## Reconversão necessária

Reconverta com `--force` o que já estiver no lake: antes da correção, só o primeiro membro de cada ZIP chegava ao lake (num teste com 3 membros e 6 linhas, o lake recebia 2). Reconverta também `sida` 2026-T3 e qualquer trimestre com CNPJ formatado, para recuperar o `cnpj_basico`.

## Saiba mais

- [Changelog do pacote](https://github.com/Quantilica/pgfn-fetcher/blob/main/CHANGELOG.md)
- [Repositório](https://github.com/Quantilica/pgfn-fetcher)
- [Proveniência e manifestos](../../conceitos/proveniencia.md) e [Parquet + Polars](../../conceitos/parquet-polars.md)
