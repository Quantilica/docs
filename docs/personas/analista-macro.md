---
title: Analista macroeconômico — caminho rápido na Quantilica
description: Indicadores, séries longas, painéis e relatórios. As 3 ferramentas e a receita inicial para quem faz acompanhamento macro do Brasil.
---

# Analista macroeconômico

Você acompanha PIB, IPCA, desemprego, juros e câmbio. Tira gráficos para reuniões semanais, escreve notas, alimenta modelos de projeção. Seu inimigo silencioso é dado obsoleto, série revisada sem aviso, e quinze fontes diferentes em quinze formatos.

## Suas três dores

| Dor | A ferramenta |
|---|---|
| Coletar IPCA, PIB, PNAD, IBC-Br sem virar especialista em URL do SIDRA | **[`sidra-fetcher`](../ibge/sidra-fetcher.md)** |
| Yield curve, retorno de carteira de renda fixa, prêmio de risco fiscal | **[`tesouro-direto-fetcher`](../tesouro/tesouro-direto-fetcher.md)** + **[`rtn-fetcher`](../tesouro/rtn-fetcher.md)** |
| Reproduzir o número exato de um relatório anterior depois que a fonte revisou | **[Proveniência & Manifestos](../concepts/proveniencia.md)** |

## Por onde começar

1. **5 minutos:** baixe IPCA pelo [Quickstart aba IBGE](../quickstart.md). Confirme que a API responde e que sua máquina está pronta.
2. **15 minutos:** rode a receita **[Curva de Phillips brasileira](../cookbook/curva-phillips.md)** — IPCA × PNAD-C mensal, gráfico pronto.
3. **30 minutos:** monte o painel multi-fonte da receita **[Análise Econômica Multi-Fonte](../cookbook/analise-economica-multi-fonte.md)** — IBGE + Tesouro + emprego em um único fluxo.

### IPCA em 10 linhas

```python
from sidra_fetcher import SidraClient
from sidra_fetcher.sidra import Parametro, Formato, Precisao
import polars as pl

param = Parametro(
    agregado="1737",               # IPCA mensal por componente
    territorios={"1": ["all"]},    # Brasil
    variaveis=["2266"],            # variação mensal (%)
    periodos=[],
    classificacoes={},
    formato=Formato.A,
    decimais={"": Precisao.M},
)
with SidraClient(timeout=60) as client:
    df = pl.DataFrame(client.get(param.url()))

print(df.select(["D2N", "V"]).tail(12))  # últimos 12 meses
```

## O conceito que importa para você

> **[Reprodutibilidade](../concepts/principios.md#reprodutibilidade)** — o IBGE revisa séries históricas com frequência. Sem proveniência, o número do relatório de janeiro não bate com o número da auditoria de junho. Saiba como o manifesto SHA-256 resolve isso na página [Proveniência](../concepts/proveniencia.md).

## Padrões que economizam tempo

- **Cacheie metadados** com `save_agregado`/`load_agregado` — eles mudam pouco. Salve uma vez, recarregue do disco nas próximas execuções.
- **Filtre períodos no servidor** — não baixe a série inteira se você só precisa dos últimos 5 anos. Use `Parametro(periodos=["202301", ...])`.
- **Use `AsyncSidraClient` para múltiplos agregados** — buscar PIB, IPCA, IBC-Br concorrentemente é 3x mais rápido que sequencial.

## Caminho de aprofundamento

- [`sidra-pipelines`](../ibge/sidra-pipelines.md) — catálogo de 30+ pipelines IBGE prontos para carregar em PostgreSQL.
- [`sidra-sql`](../ibge/sidra-sql.md) — quando seu fluxo virou pipeline e você quer warehouse com SCD II.
- [Cookbook completo](../cookbook/index.md) — receitas que você pode parafrasear.
