---
title: Engenheiro de dados — caminho rápido na Quantilica
description: Pipelines, warehouse, data contracts e proveniência criptográfica. A stack Quantilica para quem constrói a infraestrutura.
---

# Engenheiro de dados / ETL

Você é responsável pela infraestrutura que serve os analistas. Constrói pipelines reprodutíveis, atende SLAs de freshness, e responde quando o dashboard mostra valor errado. Não tem paciência para coletor frágil ou formato proprietário.

## Suas três dores

| Dor | A ferramenta |
|---|---|
| Cada nova fonte exigia retry, manifesto, logging e exceção customizada | **[`quantilica-core`](../../fundacoes/quantilica-core.md)** |
| Encoding inconsistente, schemas mutantes, falta de tipagem na ingestão | **[`quantilica-analytics`](../../fundacoes/quantilica-analytics.md)** (Data Contracts) |
| Carregar SIDRA em PostgreSQL com revisões preservadas (versões por arquivo) | **[`quantilica-sql`](../../fundacoes/quantilica-sql.md#sidra-ibge_sidra)** |

## Por onde começar

1. **5 minutos:** leia a [Arquitetura](../../conceitos/arquitetura.md). Entenda como `-fetcher`, `-sql` e `-pipelines` se conectam.
2. **15 minutos:** rode um pipeline declarativo via `quantilica sql plugin install ... --alias std && quantilica sql run ibge/precos/snipc`. Isso é o "fim do túnel" — pipelines como TOML versionado.
3. **30 minutos:** monte a receita **[Balança comercial em DuckDB](../receitas/balanca-duckdb.md)** — `comex-fetcher` para baixar, DuckDB para consultar Parquet sem RAM.

### Pipeline de inflação em 3 comandos

```bash
# 1. Coletar as tabelas do SNIPC (uma vez, ou a cada revisão)
quantilica ibge-sidra sync 7060 -o ./data/ibge-sidra

# 2. Carregar o bruto no PostgreSQL (só a versão vigente de cada consulta)
quantilica sql load sidra --source-path ./data/ibge-sidra --all

# 3. Instalar o catálogo e rodar o pipeline SNIPC → materializa INPC, IPCA e IPCA-15
quantilica sql plugin install https://github.com/Quantilica/quantilica-pipelines.git --alias std
quantilica sql run ibge/precos/snipc
```

```python
# Verificar manifesto de execução gerado automaticamente
import json
from pathlib import Path

manifests = list(Path("manifests/").glob("*.execution.json"))
latest = json.loads(manifests[-1].read_text())
print(latest["rows_loaded"], "linhas carregadas")
print(latest["sha256"])  # hash do arquivo de origem
```

## Os conceitos que importam para você

- **[Modularidade](../../conceitos/principios.md#modularidade)** — cada fetcher tem suas próprias deps e retry. Sem mega-fetcher.
- **[Resiliência](../../conceitos/principios.md#resiliência)** — backoff exponencial, retomada, idempotência.
- **[Proveniência & Manifestos](../../conceitos/proveniencia.md)** — SHA-256 ao lado de cada artefato, embarcado em Parquet.
- **[Parquet + Polars](../../conceitos/parquet-polars.md)** — o formato analítico padrão do ecossistema.

## Padrões que escalam

- **Manifestos no git, dados fora.** Versionar `.manifest.json` no repositório do projeto, manter os arquivos em S3/MinIO. O manifesto é a fonte de verdade.
- **TOML > código Python para pipelines repetitivos.** O `quantilica-sql` aceita pipelines declarativos. Versionados, lintáveis, lidos por não-devs.
- **`COPY FROM STDIN` em vez de `INSERT`.** Cerca de 100 mil linhas/s no SIDRA do `quantilica-sql`, contra horas para 10M linhas com `INSERT`. O `quantilica-sql` já faz isso.
- **Versão nova, nunca sobrescrever.** Nunca sobrescreva dado oficial; a revisão entra como versão nova e a antiga fica inativa (`ativo = FALSE`), consultável com `dados_em`. Auditoria gratuita.
- **DuckDB sobre Parquet.** Para queries ad-hoc em bilhões de linhas sem provisionar warehouse.

## Caminho de aprofundamento

- [`quantilica-core` — anatomia de um download](../../fundacoes/quantilica-core.md)
- [`quantilica-analytics` — Parquet com proveniência embarcada](../../fundacoes/quantilica-analytics.md)
- [`quantilica-sql` — warehouse, versões e `dados_em`](../../fundacoes/quantilica-sql.md)
- [Padrões Práticos](../../conceitos/padroes.md) — receitas táticas para casos comuns.
