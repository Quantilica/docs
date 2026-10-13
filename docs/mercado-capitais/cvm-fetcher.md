---
title: cvm-fetcher — Dados abertos da CVM
description: Coletor dos conjuntos de dados abertos da Comissão de Valores Mobiliários, organizados por grupo.
---

# `cvm-fetcher`

O `cvm-fetcher` coleta os conjuntos de dados abertos da CVM publicados em `dados.cvm.gov.br`.

## Instalação

```bash
quantilica install cvm
```

## Grupos disponíveis

Cada conjunto pertence a um grupo. Para a lista completa, use `quantilica cvm list`. Os principais:

| Área | Grupos (ID) |
|---|---|
| Cadastros | `cia-cad`, `fi-cad`, `intermed-cad`, `auditor-cad`, `agente-auton-cad`, `consultor-cad`, `adm-cart-cad`, `agente-fiduc-cad` |
| Companhias abertas | `cia-dfp` (demonstrações financeiras padronizadas), `cia-itr` (informações trimestrais), `cia-fre` (formulário de referência), `cia-fca` (formulário cadastral), `cia-ipe` (informações periódicas e eventuais), `cia-cgvn` |
| Fundos de investimento | `fi-inf-diario`, `fi-cda`, `fi-extrato`, `fi-lamina`, `fi-perfil`, `fi-balancete`, `fi-entrega` |
| FII, FIDC, FIAGRO e FIP | `fii-inf-mensal`, `fii-inf-trim`, `fii-inf-anual`, `fii-dfin`, `fidc-inf-mensal`, `fiagro-inf-mensal`, `fip-inf` |
| Ofertas e securitização | `ofertas`, `securit-cra`, `securit-cri` |

## Como usar

Verificar o que está desatualizado no remoto, sem baixar:

```bash
quantilica cvm check
```

Baixar um ou mais grupos:

```bash
quantilica cvm sync cia-dfp fi-inf-diario -o ./data/cvm
```

Converter os arquivos brutos já baixados (o padrão de entrada e de saída é `/data/cvm`):

```bash
quantilica cvm convert -i ./data/cvm -o ./data/cvm/parquet
```

Para uso como biblioteca dentro de um projeto, instale com `uv add cvm-fetcher --index https://index.quantilica.com/simple/`.
