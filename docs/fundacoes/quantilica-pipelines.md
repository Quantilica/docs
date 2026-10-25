---
title: quantilica-pipelines — Catálogo de pipelines
description: Catálogo declarativo de pipelines ETL e modelos analíticos em SQL para o quantilica-sql, organizado por domínio. Substitui sidra-pipelines e bcb-sgs-pipelines.
---

# `quantilica-pipelines`

O `quantilica-pipelines` é o catálogo oficial de pipelines do [`quantilica-sql`](quantilica-sql.md): definições em TOML e SQL que transformam os dados brutos carregados no PostgreSQL em tabelas analíticas prontas para consulta. Ele **substitui** os catálogos `sidra-pipelines` e `bcb-sgs-pipelines`, que seguem documentados enquanto você migra.

| | |
|---|---|
| **Versão** | 1.0.0 (o catálogo não é um pacote Python: não tem `pyproject.toml` nem wheel) |
| **Conteúdo** | 34 pipelines (contagem de 2026-10-25, por arquivos `transform.toml`) |
| **Domínios** | `macro/` (9), `ibge/` (20), `setorial/` (4) e `cross/` (1) |
| **Instalação** | plugin do `quantilica-sql`, direto do repositório Git |

## Instalação

Com o [`quantilica-sql`](quantilica-sql.md) instalado:

```bash
quantilica sql plugin install https://github.com/Quantilica/quantilica-pipelines.git --alias std
quantilica sql plugin list
```

O alias (`std` aqui) identifica o catálogo na lista de plugins. Para tirar o catálogo: `quantilica sql plugin remove`.

## Executando

```bash
quantilica sql run macro/juros
quantilica sql run cross/macro_trabalho
```

Cada execução lê as tabelas brutas já carregadas, aplica o SQL do pipeline e grava o resultado no schema `analytics`. `--target-schema` muda o destino, útil para testar sem tocar nas tabelas de produção. Os dados brutos precisam estar carregados antes: baixe com o coletor da fonte e carregue com `quantilica sql load`.

## Anatomia de um pipeline

Cada pipeline é uma pasta com três tipos de arquivo. O exemplo é `macro/juros`:

```text
macro/juros/
├── fetch.toml       # quais dados brutos o pipeline usa
├── transform.toml   # tabelas de saída, estratégia e chave primária
└── juros.sql        # o SELECT que produz a tabela
```

`fetch.toml` declara a entrada. Neste caso, séries do BCB SGS por identificador ou por tema:

```toml
[[series]]
ids = [432, 11, 12, 226]

[[series]]
themes = ["Taxas de juros"]
```

`transform.toml` declara a saída:

```toml
[[table]]
name        = "juros"
schema      = "analytics"
strategy    = "replace"
sql         = "juros.sql"
description = "Séries de taxas de juros do mercado financeiro filtradas por tema"
primary_key = ["date", "date_end", "taxa"]
```

O arquivo `.sql` é um `SELECT` (ou `WITH`) puro. O motor materializa a tabela conforme a `strategy` declarada (`replace` no exemplo).

## Catálogo

| Domínio | Conteúdo | Pipelines |
|---|---|---|
| `macro/` | Atividade, câmbio, commodities, crédito, juros, moeda, preços do BCB, movimento de câmbio contratado e PIB mensal | 9 |
| `ibge/` | Agropecuária (abate, couro, estoques, leite, LSPA, PAM, PEVS, POG, PPM), contas nacionais, indústria, comércio (PMC), serviços (PMS), população, preços (IPP, SINAPI, SNIPC) e PNAD Contínua mensal | 20 |
| `setorial/` | Álcool carburante, derivados de petróleo, desembolsos do BNDES e energia elétrica | 4 |
| `cross/` | Modelos que cruzam domínios, como `macro_trabalho` (macro e mercado de trabalho) | 1 |

O `manifest.toml` na raiz do repositório registra os pipelines por tema, com caminho e descrição.

!!! note "Um pipeline por vez"

    Os pipelines do IBGE podem ter milhões de linhas na primeira execução. Rode um por vez e confira o resultado antes de passar ao próximo.

## Criando o seu catálogo

O `quantilica-sql` gera o esqueleto de um pipeline ou de um catálogo completo, com `manifest.toml` e `README.md`:

```bash
quantilica sql scaffold meu_pipeline --type ibge
quantilica sql scaffold meu_catalogo --catalog --description "Meu catálogo"
```

Publique o repositório no Git e instale com `quantilica sql plugin install <url>`.

## Migrando dos catálogos legados

| Legado | `quantilica-pipelines` |
|---|---|
| `sidra-pipelines` (`sidra-sql run std <pipeline>`) | pipelines das áreas correspondentes em `ibge/`, executados com `quantilica sql run ibge/<área>/<pipeline>` |
| `bcb-sgs-pipelines` (`bcb-sgs-sql run std <pipeline>`) | pipelines em `macro/`, executados com `quantilica sql run macro/<pipeline>` |

Os pipelines agora são identificados por `<domínio>/<pipeline>`, não mais por um nome plano. Confira a lista no `manifest.toml` e nas pastas do repositório, porque os nomes e a organização nem sempre coincidem com os dos catálogos legados. As páginas dos catálogos legados continuam em [sidra-pipelines](../fontes/ibge/sidra-pipelines.md) e [bcb-sgs-pipelines](../fontes/bcb/bcb-sgs-pipelines.md).

## Saiba mais

- [Changelog do catálogo](https://github.com/Quantilica/quantilica-pipelines/blob/main/CHANGELOG.md)
- [Repositório](https://github.com/Quantilica/quantilica-pipelines)
- [quantilica-sql](quantilica-sql.md)
