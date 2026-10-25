---
title: tse-fetcher — Dados eleitorais do TSE
description: Baixa os datasets eleitorais do ODSele, o portal de dados abertos do TSE (candidatos, bens, prestação de contas e votação), com seleção por ano.
---

# `tse-fetcher`

O `tse-fetcher` coleta os datasets eleitorais do ODSele, o portal de dados abertos do TSE, com seleção por ano.

| | |
|---|---|
| **Fonte** | TSE, ODSele (`cdn.tse.jus.br`) |
| **Datasets** | `candidatos`, `bens`, `votacao`, `prestacao_contas` |
| **Seleção** | por dataset e por ano (`--years 2022` ou `--years 2020:2024`) |
| **Escopo do pacote** | só baixa. Não converte os arquivos |

!!! warning "Pegadinhas da fonte"

    - **Intervalo padrão de anos.** Sem `--years`, o `sync` baixa só 2018–2026, mesmo para datasets que começam antes. Para o histórico completo de candidatos, use `--years 1994:2026`.
    - **Cada dataset começa em um ano diferente.** Anos fora da cobertura de um dataset são ignorados, e o `sync` informa quantos pares dataset/ano ficaram de fora. Só existem arquivos nos anos de eleição (ver a tabela abaixo).
    - **Listagem do CDN pode devolver 403.** O diretório respondeu 403 em verificações recentes, o que pode ser bloqueio a clientes sem navegador. Revalide antes de tratar a fonte como indisponível. Ver [Status das fontes](../../status.md).

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install tse

# Ou como biblioteca no seu projeto
uv add tse-fetcher --index https://index.quantilica.com/simple/
```

**Requisitos:** Python 3.12+

## Primeiro dado

```bash
quantilica tse sync candidatos --years 2022 -o ./data/tse
```

## Datasets

| Dataset | Conteúdo | Primeiro ano | Por UF |
|---|---|---|---|
| `candidatos` | Candidatos (consulta de candidaturas) | 1994 | não |
| `bens` | Bens declarados pelos candidatos | 2006 | não |
| `prestacao_contas` | Prestação de contas eleitorais (receitas e despesas de candidatos) | 2020 | não |
| `votacao` | Votação nominal por município e zona | 1996 | não |

Os nomes `despesas` e `receitas` ainda são aceitos, mas estão descontinuados: ambos resolvem para `prestacao_contas`.

## Comandos

| Comando | O que faz |
|---|---|
| `quantilica tse list` | Lista os datasets disponíveis no ODSele |
| `quantilica tse info <dataset>` | Mostra os metadados de um dataset |
| `quantilica tse check` | Compara o disco com o remoto e mostra o plano, sem baixar. `--years`/`-y`, `--json` e `--out` |
| `quantilica tse sync` | Baixa os datasets pedidos (padrão: todos). `--years`/`-y`, `--output`/`-o` (padrão `/data/tse`), `--dry-run`, `--force` e `--from-plan` |

## Como usar

Verificar o remoto contra o local, sem baixar:

```bash
quantilica tse check --years 2022
```

Baixar datasets de um ano, ou de um intervalo de anos:

```bash
quantilica tse sync candidatos votacao --years 2022 -o ./data/tse
quantilica tse sync prestacao_contas --years 2020:2024 -o ./data/tse
```

Sem nomes de dataset, o `sync` baixa todos eles. Para atualizar só o que mudou:

```bash
quantilica tse check --years 2018:2026 --out plano.json -o ./data/tse
quantilica tse sync --from-plan plano.json -o ./data/tse
```

## Saiba mais

- [Changelog do pacote](https://github.com/Quantilica/tse-fetcher/blob/main/CHANGELOG.md)
- [Repositório](https://github.com/Quantilica/tse-fetcher)
- [Proveniência e manifestos](../../conceitos/proveniencia.md)
