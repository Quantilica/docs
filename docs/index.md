---
title: Quantilica — Dados públicos brasileiros, prontos para análise
description: Ferramentas resilientes em Python para extrair, normalizar e analisar dados públicos brasileiros — IBGE, Tesouro, DATASUS, INMET, CAGED, RAIS, Comex e mais.
hide:
  - navigation
---

# Pare de raspar governo. Comece a analisar.

<div align="center">
  <img src="assets/logo.png" alt="Logo Quantilica" width="160" height="160">
</div>

**Quantilica** é uma plataforma aberta de coletores Python para os dados públicos brasileiros — IBGE, Tesouro Nacional, DATASUS, INMET, CAGED, RAIS, Comex e adjacentes. Uma ferramenta especializada por fonte, todas seguindo os mesmos princípios: resiliência, proveniência e Parquet tipado na saída.

[Comece em 5 minutos →](quickstart.md){ .md-button .md-button--primary }
[Ver o Cookbook](cookbook/index.md){ .md-button }
[GitHub](https://github.com/Quantilica){ .md-button }

---

## O atrito que você conhece

Quem já tentou trabalhar com dados oficiais brasileiros conhece o roteiro:

- A API REST do IBGE devolve `502` no meio de uma série histórica.
- O FTP do DATASUS tem 1998 escrito na cara e tomba a cada três dias úteis.
- O CSV de 50M linhas do CAGED estoura a memória do Pandas.
- O Siscomex serve arquivos GB com SSL quebrado e schemas que mudam sem aviso.
- O Tesouro publica taxas em planilhas com cabeçalhos hierárquicos e separadores `;`.
- Cada análise começa com duas semanas de yak shaving e raspagem.

Você está fazendo trabalho que outra pessoa já fez ontem. E vai refazer amanhã.

## A virada

Quantilica resolve isso de uma vez, **para todo mundo**. Uma ferramenta por fonte, todas seguindo os mesmos cinco [Princípios de Design](concepts/principios.md): Modularidade, Resiliência, Performance, Reprodutibilidade e Sem Mágica.

```python
# Baixar o IPCA cheio em 3 linhas
from sidra_fetcher.fetcher import SidraClient

with SidraClient() as client:
    agregado = client.get_agregado(1705)  # IPCA-15: metadados + 84 períodos + 27 localidades
```

Cada download vem acompanhado de um manifesto SHA-256 (proveniência total), retry automático com backoff, e saída padronizada em Parquet — pronto para Polars, DuckDB, ou o que vier.

## A promessa

Não é mais um pacote no PyPI. É **infraestrutura aberta**: quando o IBGE muda um endpoint, o ecossistema inteiro se atualiza junto. Quando o DATASUS publica um novo arquivo `.dbc`, o crawler já sabe. Quando o Tesouro reformata a planilha de taxas, o parser absorve a mudança em uma release.

A camada de confiança entre você e os dados públicos do Brasil — para que você volte a fazer o trabalho que importa.

---

## Uma ferramenta por dor

| Ferramenta | A dor que ela elimina |
|---|---|
| **[sidra-fetcher](ibge/sidra-fetcher.md)** | API REST do IBGE instável, rate limiting, períodos em strings ambíguas |
| **[sidra-sql](ibge/sidra-sql.md)** | Bulk load de SIDRA em PostgreSQL com histórico de revisões (SCD II) |
| **[sidra-pipelines](ibge/sidra-pipelines.md)** | Catálogo declarativo de pipelines IBGE prontos para rodar |
| **[tesouro-direto-fetcher](tesouro/tesouro-direto-fetcher.md)** | CKAN do Tesouro, leitores por dataset, gráficos prontos |
| **[rtn-fetcher](tesouro/rtn-fetcher.md)** | Planilhas hierárquicas do RTN viradas em DataFrame tipado |
| **[pdet-fetcher](trabalho/pdet-fetcher.md)** | CAGED/RAIS de 50M+ linhas, processadas com Polars sem estourar memória |
| **[comex-fetcher](comex/comex-fetcher.md)** | Siscomex com SSL ruim, arquivos GB, downtime governamental |
| **[datasus-fetcher](saude/datasus-fetcher.md)** | FTP legado do DATASUS, crawler multithread, 320+ GB de microdados |
| **[inmet-fetcher](clima/inmet-fetcher.md)** | INMET BDMEP, séries climáticas históricas com encoding limpo |
| **[quantilica-core](fundacoes/quantilica-core.md)** | A fundação: HTTP resiliente, storage atômico, manifestos SHA-256 |
| **[quantilica-io](fundacoes/quantilica-io.md)** | Parquet tipado com proveniência injetada no header |

---

## Por onde começar

### Em 5 minutos
- **[Quickstart](quickstart.md)** — instala, baixa um dataset real, plota um gráfico. Três caminhos: IBGE, Tesouro, Saúde.

### Aprofundar
1. **[Arquitetura da Plataforma](concepts/arquitetura.md)** — como as partes se conectam.
2. **[Princípios de Design](concepts/principios.md)** — por que o sistema tem essa forma.
3. **[Padrões Práticos](concepts/padroes.md)** — receitas táticas que materializam os princípios.
4. **[Parquet + Polars](concepts/parquet-polars.md)** — o formato e a biblioteca que sustentam tudo.

### Pela dor
| Você quer… | Vá para |
|---|---|
| Indicadores macro (PIB, IPCA, desemprego) | [IBGE](ibge/index.md) |
| Yield curve e retornos do Tesouro Direto | [Tesouro](tesouro/index.md) |
| Salários e fluxos de emprego (CAGED/RAIS) | [Trabalho](trabalho/index.md) |
| Fluxos de comércio exterior | [Comércio Exterior](comex/comex-fetcher.md) |
| Microdados de saúde pública | [Saúde Pública](saude/datasus-fetcher.md) |
| Séries climáticas históricas | [Clima](clima/inmet-fetcher.md) |
| Cruzar múltiplos domínios | [Cookbook](cookbook/index.md) |

---

## Stack e padrões

- **Python 3.12+**, `uv` para ambientes e dependências.
- **`hatchling`** como build system, **`ruff`** para lint/format, **`pytest`** para testes.
- **Parquet + Polars** como destino analítico padrão.
- **MIT** para quase tudo (GPL-3.0 só no `tesouro-direto-fetcher`).
- Distribuição via `git+https://` para quase tudo; **`datasus-fetcher`** publicado no PyPI.

Veja os [Princípios de Design](concepts/principios.md) para o detalhe completo, ou pule direto para o [Quickstart](quickstart.md).

---

## Contribuir

Encontrou um fetcher quebrado porque o governo mudou um endpoint? Quer sugerir uma nova fonte? Tem uma receita interessante para o Cookbook?

- **Bug em fetcher** → abra uma issue no repositório específico.
- **Nova fonte de dados** → use o template *Feature Request* no GitHub.
- **Receita de cruzamento** → PR no `docs/` com um novo arquivo em `cookbook/`.

Os padrões técnicos estão em [CONTRIBUTING.md](https://github.com/Quantilica/.github/blob/main/CONTRIBUTING.md) e em [DOCUMENTATION.md](https://github.com/Quantilica/.github/blob/main/DOCUMENTATION.md).
