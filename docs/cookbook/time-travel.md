---
title: Reproduzir um paper de 2019 — Time Travel com manifestos
description: Como o manifesto SHA-256 + SCD II do sidra-sql permitem reproduzir um número exato anos depois, mesmo após revisão silenciosa do IBGE.
---

# Reproduzir um paper de 2019 — Time Travel real

> **Tempo estimado:** 20 minutos. **Pacotes:** `sidra-sql` + PostgreSQL.

Você publicou um relatório em 2019 com o PIB municipal por estado. Em 2026, alguém pede para reproduzir a Tabela 4 — número exato. Só que o IBGE revisou a série em 2021. Como provar que o seu número original estava certo?

Esta receita mostra como a infraestrutura Quantilica resolve isso com **dois mecanismos** que trabalham juntos: manifesto SHA-256 (proveniência criptográfica) + SCD Type II (snapshots preservados no warehouse).

## O que você vai aprender

- Como ler um manifesto antigo para validar que o arquivo é o mesmo.
- Como rodar uma query no `sidra-sql` "como era em 2019-12-31".
- Como anexar tudo isso ao apêndice de replicação.

## Setup

```bash
uv add "sidra-sql @ git+https://github.com/Quantilica/sidra-sql.git" "quantilica-core @ git+https://github.com/Quantilica/quantilica-core.git"
```

Assume que você já tem `sidra-sql` rodando com o pipeline `pib_municipal` carregado (veja [sidra-pipelines](../ibge/sidra-pipelines.md)).

## A receita

### Passo 1 — Validar o manifesto antigo

Você guardou (deveria ter guardado) o `.manifest.json` ao lado do paper:

```python
from quantilica_core.manifests import DownloadManifest

manifest = DownloadManifest.read_json("paper-2019/pib-municipal.json.manifest.json")

print(manifest.sha256)         # 'a3f9...'
print(manifest.downloaded_at)  # '2019-12-15T14:23:01Z'
print(manifest.url)            # endpoint exato com parâmetros
print(manifest.producer)       # 'sidra-fetcher@0.3.1'
```

Se você ainda tem o arquivo bruto, confirme o hash:

```python
if manifest.verify("paper-2019/pib-municipal.json"):
    print("Arquivo idêntico ao da publicação.")
```

### Passo 2 — Query "como era em 2019-12-31" no warehouse

O `sidra-sql` carrega dados com SCD Type II — toda revisão fica como linha nova, sem sobrescrever a antiga. Para reproduzir:

```sql
-- Tabela analítica padrão sobre o warehouse SIDRA
SELECT
    l.d1c     AS codigo_municipio,
    l.d1n     AS nome_municipio,
    p.ano,
    dim.d2n   AS variavel,
    d.v::numeric AS valor
FROM ibge_sidra.dados d
JOIN ibge_sidra.localidade l ON d.localidade_id = l.id
JOIN ibge_sidra.periodo    p ON d.periodo_id    = p.id
JOIN ibge_sidra.dimensao   dim ON d.dimensao_id = dim.id
WHERE d.tabela_sidra_id = '5938'              -- PIB municipal
  AND d.modificacao <= DATE '2019-12-15'      -- ↪ sua data de corte
  AND d.ativo = TRUE                          -- ↪ versão vigente naquela data
  AND p.ano BETWEEN 2010 AND 2017
ORDER BY l.d1c, p.ano;
```

A condição-chave é `d.modificacao <= '2019-12-15'`. O `ativo = TRUE` filtra a versão que estava vigente naquela data — ignorando revisões publicadas depois.

### Passo 3 — Comparar com a versão atual

Para mostrar a diferença introduzida pela revisão de 2021:

```sql
WITH original AS (
    SELECT l.d1c AS mun, p.ano, d.v::numeric AS valor_2019
    FROM ibge_sidra.dados d
    JOIN ibge_sidra.localidade l ON d.localidade_id = l.id
    JOIN ibge_sidra.periodo    p ON d.periodo_id    = p.id
    WHERE d.tabela_sidra_id = '5938'
      AND d.modificacao <= DATE '2019-12-15'
      AND d.ativo = TRUE
),
atual AS (
    SELECT l.d1c AS mun, p.ano, d.v::numeric AS valor_atual
    FROM ibge_sidra.dados d
    JOIN ibge_sidra.localidade l ON d.localidade_id = l.id
    JOIN ibge_sidra.periodo    p ON d.periodo_id    = p.id
    WHERE d.tabela_sidra_id = '5938'
      AND d.ativo = TRUE
)
SELECT
    o.mun, o.ano, o.valor_2019, a.valor_atual,
    (a.valor_atual - o.valor_2019) / NULLIF(o.valor_2019, 0) AS variacao_pct
FROM original o
JOIN atual a USING (mun, ano)
WHERE o.valor_2019 IS DISTINCT FROM a.valor_atual
ORDER BY ABS(variacao_pct) DESC
LIMIT 20;
```

O resultado mostra exatamente onde a revisão do IBGE impactou — útil para nota técnica, errata, ou apêndice.

## O que está acontecendo

- **Manifesto SHA-256** prova que o arquivo bruto de 2019 é exatamente o que alimentou a análise. Não é fé — é hash.
- **SCD Type II no warehouse** preserva todas as versões. A coluna `modificacao` registra quando cada linha foi publicada pelo IBGE; `ativo` marca se ela foi superada.
- **`modificacao <= data_corte`** é o "tempo de viagem" — você consegue rodar qualquer query como ela rodaria naquela data.

## Pegadinhas

- **Você precisa ter ingerido em 2019, não só hoje.** Se você só começou a usar o `sidra-sql` agora, as revisões anteriores estão sobrescritas pelo IBGE — `modificacao` vai marcar o dia de hoje para tudo. **Comece a guardar o histórico desde já, mesmo que não precise ainda.**
- **Manifesto sem arquivo é fraco.** Guardar só o `.manifest.json` permite verificar que o arquivo original tinha aquele hash, mas você precisa de uma cópia do dado em algum lugar (Zenodo, S3, HD). O manifesto sozinho prova quem você é, não o que disse.
- **`ativo` pode mentir.** Se você nunca re-rodou o pipeline, todas as linhas continuam `ativo=TRUE` mesmo se o IBGE revisou. O time travel só funciona se o pipeline for re-executado periodicamente.

## Anexo de replicação — o que entregar ao referee

Para o apêndice metodológico do paper, anexe:

1. **`pib-municipal.json.manifest.json`** versionado no repositório do paper.
2. **A query SQL** com `modificacao <= 'YYYY-MM-DD'` literal, sem variáveis.
3. **A versão do `sidra-sql`** e do `sidra-fetcher` usadas (output de `pip show`).
4. **Um README** mostrando como subir o warehouse a partir do zero e rodar a query.

Quatro arquivos. Zero ambiguidade.

## Veja também

- [Proveniência & Manifestos](../concepts/proveniencia.md)
- [sidra-sql — Governança de Dados](../ibge/sidra-sql.md)
- [Pesquisador acadêmico](../personas/pesquisador.md) — atalhos para esse perfil.
- [Princípios — Reprodutibilidade](../concepts/principios.md#reprodutibilidade)
