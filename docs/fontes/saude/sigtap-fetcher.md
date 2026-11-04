---
title: sigtap-fetcher — Tabela de procedimentos do SUS (SIGTAP)
description: Baixa a Tabela Unificada do SIGTAP no FTP do DATASUS por competência e converte as 41 tabelas para o lake Hive em Parquet, particionado por competência.
---

# `sigtap-fetcher`

O `sigtap-fetcher` baixa a Tabela Unificada de Procedimentos, Medicamentos e OPM do SUS (SIGTAP) publicada no FTP do DATASUS e converte as tabelas para o lake Hive em Parquet.

| | |
|---|---|
| **Fonte** | DATASUS, FTP `ftp2.datasus.gov.br`, diretório `/pub/sistemas/tup/downloads` |
| **Formato** | ZIP `TabelaUnificada_AAAAMM_v<timestamp>` com arquivos de largura fixa e um `<tabela>_layout.txt` por tabela |
| **Organização** | 1 grupo (`tabelas`, com aliases `padrao` e `tudo`), uma entrada por competência |
| **Escopo do pacote** | download e conversão para Parquet. A carga em banco não faz parte dele |

!!! note "Pacote ainda não publicado"

    O pacote está na branch `feat/r1` e ainda não tem release no índice. Os comandos abaixo valem a partir da primeira publicação.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install sigtap --extra analysis

# Ou como biblioteca no seu projeto
uv add 'sigtap-fetcher[analysis]' --index https://index.quantilica.com/simple/
```

O extra `analysis` é necessário para a conversão ao lake.

**Requisitos:** Python 3.12+

## Primeiro dado

```bash
quantilica sigtap list
quantilica sigtap sync -o ./data/sigtap
```

## Comandos

| Comando | O que faz |
|---|---|
| `quantilica sigtap list` | Lista as competências reais encontradas na listagem do FTP |
| `quantilica sigtap check` | Compara o disco com o FTP por competência (AAAAMM) e versão, sem baixar |
| `quantilica sigtap sync` | Baixa as competências pedidas. Padrão de saída: `/data/sigtap` |
| `quantilica sigtap convert <entrada> <lake>` | Converte o acervo bruto para o lake Hive |

## Conjuntos

O catálogo é descoberto na listagem do FTP, não calculado: desde 2025 os arquivos têm o sufixo `_v<timestamp>`, e o fetcher usa a **versão mais recente por competência**. Um sufixo `v` novo é uma versão nova (`download/new-version` no `check`).

O ZIP de 2026-10 traz **41 tabelas** (`tb_*` e `rl_*`), todas com layout próprio. Eras antigas trazem um subconjunto. `LEIA_ME.TXT` e o `layout.txt` consolidado não são tabelas e não são convertidos.

## Particionamento no lake

Cada tabela é um dataset (`tb_procedimento`, `tb_cid`, `rl_procedimento_incremento` e as demais), particionado por `competencia`. O `convert` mantém só a versão de maior `_v` de cada competência. O schema é explícito (coluna vazia nas primeiras linhas não vira `Null`). Só `vl_sh`, `vl_sa` e `vl_sp` são dinheiro (centavos divididos por 100); `vl_idade_*`, `vl_campos_irradiados` e `vl_percentual_*` são inteiros. Tabela sem `<tabela>_layout.txt` no ZIP não é convertida com o layout de outra: entra em `errors` com o nome da tabela e do ZIP.

## Política de frescor

**F1 (`HEAD_OR_MANIFEST`)** com cliente FTP: o veredito de frescor é local e casa a entrada por competência e versão, ignorando o carimbo `@AAAAMMDD` do nome local. Antes, o carimbo de hoje fazia todo arquivo baixado em outro dia virar `download/not-present` (re-download diário).

## Limitações conhecidas

- `rl_procedimento_tuss` vem vazia na fonte.
- O plano original falava em 42 tabelas; o ZIP de 2026-10 traz 41.

## Reconversão necessária

Reconverta com `--force` `tb_procedimento`, `tb_cid` e `rl_procedimento_incremento`: campos como idades e percentuais eram divididos por 100 por engano. Reconverta também competências convertidas antes de `convert` manter só a versão mais recente.

## Saiba mais

- [Changelog do pacote](https://github.com/Quantilica/sigtap-fetcher/blob/main/CHANGELOG.md)
- [Repositório](https://github.com/Quantilica/sigtap-fetcher)
- [Proveniência e manifestos](../../conceitos/proveniencia.md) e [Parquet + Polars](../../conceitos/parquet-polars.md)
