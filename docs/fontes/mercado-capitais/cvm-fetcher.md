---
title: cvm-fetcher — Dados abertos da CVM
description: Baixa os conjuntos de dados abertos da CVM por grupo (cadastros, companhias, fundos, FII/FIDC/FIAGRO/FIP e ofertas) e converte os CSVs em Parquet.
---

# `cvm-fetcher`

O `cvm-fetcher` coleta os conjuntos de dados abertos da CVM publicados em `dados.cvm.gov.br` e, com o extra `analysis`, converte os arquivos brutos em Parquet.

| | |
|---|---|
| **Fonte** | CVM, dados abertos (`dados.cvm.gov.br/dados`) |
| **Formato** | CSV e ZIP de CSV, separados por `;` |
| **Organização** | grupos (um por conjunto de dados) e cinco macro-aliases por área |
| **Escopo do pacote** | download e conversão para Parquet. A carga em banco não faz parte dele |

!!! note "Cada conjunto tem o seu ritmo"

    Cadastros, informes diários, demonstrações anuais e ofertas são atualizados em ritmos diferentes. Por isso o pacote trata cada grupo de forma independente: o `check` mostra o que mudou em cada um, e o `sync` baixa só os grupos que você pedir.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install cvm

# Ou como biblioteca no seu projeto
uv add cvm-fetcher --index https://index.quantilica.com/simple/
```

A conversão para Parquet e a leitura (`cvm_fetcher.reader`) exigem o extra `analysis`:

```bash
quantilica install cvm --extra analysis
# ou, no seu projeto:
uv add 'cvm-fetcher[analysis]' --index https://index.quantilica.com/simple/
```

**Requisitos:** Python 3.12+

## Primeiro dado

```bash
quantilica cvm sync cia-cad -o ./data/cvm
```

O cadastro de companhias abertas (`cia-cad`) é um bom primeiro teste do fluxo.

## Comandos

| Comando | O que faz |
|---|---|
| `quantilica cvm list` | Lista os arquivos de cada grupo |
| `quantilica cvm check` | Compara o disco com o remoto e mostra o que está desatualizado, sem baixar. `--json` e `--out` exportam o plano |
| `quantilica cvm sync` | Baixa os grupos pedidos (padrão: todos). `--workers` (padrão 4), `--dry-run`, `--force` e `--from-plan` |
| `quantilica cvm convert` | Converte os CSVs e ZIPs já baixados em Parquet. `-i` define a origem e `-o` o destino (padrão de ambos: `/data/cvm`) |

## Grupos disponíveis

Cada conjunto pertence a um grupo; `quantilica cvm list` mostra os arquivos de cada um.

| Área (macro-alias) | Grupos (ID) |
|---|---|
| Cadastros (`cadastros`) | `cia-cad`, `fi-cad`, `intermed-cad`, `auditor-cad`, `agente-auton-cad`, `consultor-cad`, `adm-cart-cad`, `agente-fiduc-cad` |
| Companhias abertas (`cias`) | `cia-dfp` (demonstrações financeiras padronizadas), `cia-itr` (informações trimestrais), `cia-fre` (formulário de referência), `cia-fca` (formulário cadastral), `cia-ipe` (informações periódicas e eventuais), `cia-cgvn` |
| Fundos de investimento (`fundos`) | `fi-inf-diario`, `fi-cda`, `fi-extrato`, `fi-lamina`, `fi-perfil`, `fi-balancete`, `fi-entrega` |
| FII, FIDC, FIAGRO e FIP (`estruturados`) | `fii-inf-mensal`, `fii-inf-trim`, `fii-inf-anual`, `fii-dfin`, `fidc-inf-mensal`, `fiagro-inf-mensal`, `fip-inf` |
| Ofertas e securitização (`ofertas`) | `ofertas`, `securit-cra`, `securit-cri` |

Passe um macro-alias no lugar dos grupos individuais para baixar a área inteira:

```bash
quantilica cvm sync cias -o ./data/cvm
```

## Fluxo recomendado

Verificar o que está desatualizado no remoto, sem baixar, e baixar só isso:

```bash
quantilica cvm check --out plano.json -o ./data/cvm
quantilica cvm sync --from-plan plano.json -o ./data/cvm
```

Baixar um ou mais grupos:

```bash
quantilica cvm sync cia-dfp fi-inf-diario -o ./data/cvm
```

Converter os arquivos brutos já baixados:

```bash
quantilica cvm convert -i ./data/cvm -o ./data/cvm/parquet
```

A conversão lê CSVs soltos e CSVs dentro de ZIPs, com separador `;` e tratamento de encoding, e grava um Parquet por arquivo. Quando o arquivo de origem tem manifest, a proveniência vai para os metadados do Parquet.

## Saiba mais

- [Changelog do pacote](https://github.com/Quantilica/cvm-fetcher/blob/main/CHANGELOG.md)
- [Repositório](https://github.com/Quantilica/cvm-fetcher)
- [Proveniência e manifestos](../../conceitos/proveniencia.md) e [Parquet + Polars](../../conceitos/parquet-polars.md)
