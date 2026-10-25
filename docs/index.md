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

**Quantilica** é um ecossistema aberto de coletores Python para os dados públicos brasileiros — IBGE, Tesouro Nacional, DATASUS, INMET, CAGED, RAIS, Comex e adjacentes. Uma ferramenta especializada por fonte, todas seguindo os mesmos princípios: resiliência, proveniência e Parquet tipado na saída.

[Comece em 5 minutos →](quickstart.md){ .md-button .md-button--primary }
[Ver as receitas](guias/receitas/index.md){ .md-button }
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

Quantilica resolve isso de uma vez, **para todo mundo**. Uma ferramenta por fonte, todas seguindo os mesmos cinco [Princípios de Design](conceitos/principios.md): Modularidade, Resiliência, Performance, Reprodutibilidade e Sem Mágica.

```python
# Baixar o IPCA cheio em 3 linhas
from sidra_fetcher.fetcher import SidraClient

with SidraClient() as client:
    agregado = client.get_agregado(1705)  # IPCA-15: metadados + 84 períodos + 27 localidades
```

Cada download vem acompanhado de um manifesto SHA-256 (proveniência total), retry automático com backoff, e saída padronizada em Parquet — pronto para Polars, DuckDB, ou o que vier.

## A promessa

Não é só mais um pacote no PyPI. É **infraestrutura aberta**: quando o IBGE muda um endpoint, o ecossistema inteiro se atualiza junto. Quando o DATASUS publica um novo arquivo `.dbc`, o crawler já sabe. Quando o Tesouro reformata a planilha de taxas, o parser absorve a mudança em uma release.

A camada de confiança entre você e os dados públicos do Brasil — para que você volte a fazer o trabalho que importa.

---

## Uma ferramenta por dor

| Ferramenta | A dor que ela elimina |
|---|---|
| **[sidra-fetcher](fontes/ibge/sidra-fetcher.md)** | API REST do IBGE instável, rate limiting, períodos em strings ambíguas |
| **[sidra-sql](fontes/ibge/sidra-sql.md)** | Bulk load de SIDRA em PostgreSQL com histórico de revisões (SCD II) |
| **[sidra-pipelines](fontes/ibge/sidra-pipelines.md)** | Catálogo declarativo de pipelines IBGE prontos para rodar |
| **[tesouro-direto-fetcher](fontes/tesouro/tesouro-direto-fetcher.md)** | CKAN do Tesouro, leitores por dataset, gráficos prontos |
| **[rtn-fetcher](fontes/tesouro/rtn-fetcher.md)** | Planilhas hierárquicas do RTN viradas em DataFrame tipado |
| **[pdet-fetcher](fontes/trabalho/pdet-fetcher.md)** | CAGED/RAIS de 50M+ linhas, processadas com Polars sem estourar memória |
| **[comex-fetcher](fontes/comex/comex-fetcher.md)** | Siscomex com SSL ruim, arquivos GB, downtime governamental |
| **[datasus-fetcher](fontes/saude/datasus-fetcher.md)** | FTP legado do DATASUS, crawler multithread, mais de 400 GB de microdados |
| **[inmet-fetcher](fontes/clima/inmet-fetcher.md)** | INMET BDMEP, séries climáticas históricas com encoding limpo |
| **[bcb-sgs-fetcher](fontes/bcb/bcb-sgs-fetcher.md)** | SGS/BCB sem API de metadados, séries diárias truncadas, scraping stateful |
| **[bcb-sgs-sql](fontes/bcb/bcb-sgs-sql.md)** | Bulk load de séries do BCB SGS em PostgreSQL com histórico de revisões (soft-versioning) |
| **[bcb-sgs-pipelines](fontes/bcb/bcb-sgs-pipelines.md)** | Catálogo declarativo de 13 pipelines macro BCB prontos para rodar |
| **[anac-fetcher](fontes/aviacao/anac-fetcher.md)** | Dados abertos da Aviação Civil (voos, aeronaves, aeródromos) |
| **[anp-fetcher](fontes/petroleo/anp-fetcher.md)** | Dados de preços de combustíveis, produção, vendas e royalties |
| **[inep-fetcher](fontes/educacao/inep-fetcher.md)** | Download dos microdados educacionais do INEP por grupo (ENEM, SAEB, ENADE e outros) |
| **[rfb-cnpj-fetcher](fontes/empresas/rfb-cnpj-fetcher.md)** | Download paralelo dos ZIPs da base inteira de CNPJs (cerca de 29 GB descompactada) |
| **[cvm-fetcher](fontes/mercado-capitais/cvm-fetcher.md)** | Cadastros, companhias, fundos e ofertas da CVM, por grupo, com download independente |
| **[b3-fetcher](fontes/mercado-capitais/b3-fetcher.md)** | Cotações históricas da B3 desde 1986: arquivos de largura fixa lidos em Polars, com preços em `Decimal` exato |
| **[tse-fetcher](fontes/politica/tse-fetcher.md)** | Candidaturas, bens, prestação de contas e votação por município e zona, por ano |
| **[quantilica-core](fundacoes/quantilica-core.md)** | A fundação: HTTP resiliente, storage atômico, manifestos SHA-256 |
| **[quantilica-cli](fundacoes/quantilica-cli.md)** | O ponto de entrada único: `quantilica <fonte>` com instalação sob demanda |
| **[quantilica-analytics](fundacoes/quantilica-analytics.md)** | Parquet tipado com proveniência injetada no header |
| **[quantilica-catalog](fundacoes/quantilica-catalog.md)** | Modelo canônico de observações para cruzamento multi-fonte |
| **[quantilica-sql](fundacoes/quantilica-sql.md)** | Carga idempotente em PostgreSQL das 15 fontes e execução de pipelines analíticos |
| **[quantilica-pipelines](fundacoes/quantilica-pipelines.md)** | Catálogo de 34 pipelines SQL declarativos, por domínio, para o quantilica-sql |

---

## Por onde começar

### Em 5 minutos
- **[Quickstart](quickstart.md)** — instala, baixa um dataset real, plota um gráfico. Quatro caminhos prontos: IBGE, Tesouro, Saúde e Clima.

### Aprofundar
1. **[Arquitetura do Ecossistema](conceitos/arquitetura.md)** — como as partes se conectam.
2. **[Princípios de Design](conceitos/principios.md)** — por que o sistema tem essa forma.
3. **[Padrões Práticos](conceitos/padroes.md)** — receitas táticas que materializam os princípios.
4. **[Parquet + Polars](conceitos/parquet-polars.md)** — o formato e a biblioteca que sustentam tudo.

### Pela dor
| Você quer… | Vá para |
|---|---|
| Indicadores macro (PIB, IPCA, desemprego) | [IBGE](fontes/ibge/index.md) |
| Yield curve e retornos do Tesouro Direto | [Tesouro](fontes/tesouro/index.md) |
| Salários e fluxos de emprego (CAGED/RAIS) | [Trabalho](fontes/trabalho/index.md) |
| Fluxos de comércio exterior | [Comércio Exterior](fontes/comex/comex-fetcher.md) |
| Microdados de saúde pública | [Saúde Pública](fontes/saude/datasus-fetcher.md) |
| Séries climáticas históricas | [Clima](fontes/clima/inmet-fetcher.md) |
| Cruzar múltiplos domínios | [Receitas](guias/receitas/index.md) |
| Aviação civil e aeródromos | [Aviação Civil](fontes/aviacao/index.md) |
| Preços de combustíveis e exploração | [Petróleo e Gás](fontes/petroleo/index.md) |
| Dados educacionais (ENEM, SAEB, ENADE) | [Educação](fontes/educacao/index.md) |
| Mercado de capitais (companhias, fundos, ofertas, cotações) | [Mercado de Capitais](fontes/mercado-capitais/index.md) |
| Eleições: candidaturas, bens e votação | [Política (TSE)](fontes/politica/index.md) |
| Análise de CNPJs e quadros societários | [Empresas](fontes/empresas/index.md) |

---

## Sob o capô

Todo o ecossistema é **Python 3.12+** com `uv`, saída analítica padronizada em
**Parquet + Polars** e licença **MIT**. O detalhe de stack, distribuição e padrões técnicos
está em [Contribuir](contribuir.md); o porquê das escolhas, em
[Princípios de Design](conceitos/principios.md).

---

## Contribuir

Encontrou um fetcher quebrado porque o governo mudou um endpoint? Quer sugerir uma nova fonte? Tem uma receita interessante para o Cookbook?

- **Bug em fetcher** → abra uma issue no repositório específico.
- **Nova fonte de dados** → use o template *Feature Request* no GitHub.
- **Receita de cruzamento** → PR no `docs/` com um novo arquivo em `guias/receitas/`.

Os padrões técnicos estão em [Contribuir](contribuir.md) e em [Padrões de Escrita](normas/escrita.md).
