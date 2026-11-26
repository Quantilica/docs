---
title: Reproduzir um paper de 2019 — Time Travel com manifestos
description: Como o manifesto SHA-256 e a função dados_em do quantilica-sql reproduzem um número exato anos depois, mesmo após revisão silenciosa do IBGE.
---

# Reproduzir um paper de 2019 — Time Travel real

> **Tempo estimado:** 20 minutos. **Pacotes:** `quantilica-sql` + PostgreSQL.

Você publicou um relatório em 2019 com o PIB municipal por estado. Em 2026, alguém pede para reproduzir a Tabela 4 — número exato, vírgula por vírgula. Só que o IBGE revisou a série em 2021 e o número "atual" não bate mais com o impresso. Auditoria, banca ou tribunal: alguém vai perguntar se o seu número original estava certo. Como provar?

Esta receita mostra como a infraestrutura Quantilica resolve isso com **dois mecanismos** que trabalham juntos: manifesto SHA-256 (proveniência criptográfica) + versões preservadas no warehouse (uma por arquivo coletado, consultadas com `dados_em`).

## O que você vai aprender

- Como ler um manifesto antigo para validar que o arquivo é o mesmo.
- Como rodar uma query no `quantilica-sql` "como era em 2019-12-15", com `dados_em`.
- Como anexar tudo isso ao apêndice de replicação.

## Setup

```bash
quantilica install sql
quantilica install ibge-sidra
```

Assume um PostgreSQL com a tabela do PIB municipal (5938) carregada **com as versões antigas**. O coletor nunca apaga uma versão: uma revisão do IBGE vira um arquivo novo (`@data_nova`) ao lado do antigo, e a carga com `--historico` leva todos para o banco:

```bash
quantilica sql load sidra --source-path <raiz-do-bruto> --table 5938 --historico
```

Sem `--historico`, `--all` e `--table` carregam só a versão vigente de cada consulta, e o histórico passa a acumular a partir da próxima revisão.

## A receita

### Passo 1 — Validar o manifesto antigo

Você guardou (deveria ter guardado) o `.manifest.json` ao lado do paper:

```python
import json
import hashlib
from pathlib import Path

data = json.loads(
    Path("paper-2019/pib-municipal.json.manifest.json").read_text(encoding="utf-8")
)

print(data["sha256"])      # 'a3f9...'
print(data["fetched_at"])  # '2019-12-15T14:23:01Z'
print(data["url"])         # endpoint exato com parâmetros
print(data["producer"])    # 'ibge-sidra-fetcher'
```

Se você ainda tem o arquivo bruto, confirme o hash:

```python
content = Path("paper-2019/pib-municipal.json").read_bytes()
computed = hashlib.sha256(content).hexdigest()
if computed == data["sha256"]:
    print("Arquivo idêntico ao da publicação.")
```

### Passo 2 — Query "como era em 2019-12-15" no warehouse

O `quantilica-sql` carrega cada arquivo como uma versão (`ibge_sidra.versao`) e nunca apaga a antiga: uma revisão do IBGE fica como história, com `ativo = FALSE`. A função `dados_em(data, tabela)` devolve, para cada célula, a versão mais recente cujo `modificacao` (a data em que o IBGE publicou o período) é anterior ou igual à data de corte:

```sql
SELECT
    l.d1c     AS codigo_municipio,
    l.d1n     AS nome_municipio,
    p.ano,
    dim.d2n   AS variavel,
    d.v::numeric AS valor
FROM ibge_sidra.dados_em(DATE '2019-12-15', '5938') d   -- ↪ sua data de corte e a tabela
JOIN ibge_sidra.localidade l   ON d.localidade_id = l.id
JOIN ibge_sidra.periodo    p   ON d.periodo_id    = p.id
JOIN ibge_sidra.dimensao   dim ON d.dimensao_id   = dim.id
WHERE p.ano BETWEEN 2010 AND 2017
ORDER BY l.d1c, p.ano;
```

`dados_em` devolve as mesmas colunas de `ibge_sidra.dados`, então a consulta é a de sempre com a fonte trocada. Passe a tabela como segundo argumento: assim a função lê só as versões dela.

!!! warning "Não combine `modificacao <= data` com `ativo = TRUE`"

    Esta era a receita do `sidra-sql`, e ela **descarta** justamente o que você quer. `ativo` marca a versão vigente *hoje*; uma célula que o IBGE revisou depois de 2019 tem a versão de 2019 inativa, e o filtro `ativo = TRUE` a tira do resultado em vez de devolvê-la (onde a revisão aconteceu, a consulta volta vazia). `dados_em` resolve: ela escolhe a versão mais recente até a data, ativa ou não.

### Passo 3 — Comparar com a versão atual

Para mostrar a diferença introduzida pela revisão de 2021:

```sql
WITH original AS (
    SELECT l.d1c AS mun, p.ano, dim.d2c AS variavel, d.v::numeric AS valor_2019
    FROM ibge_sidra.dados_em(DATE '2019-12-15', '5938') d
    JOIN ibge_sidra.localidade l   ON d.localidade_id = l.id
    JOIN ibge_sidra.periodo    p   ON d.periodo_id    = p.id
    JOIN ibge_sidra.dimensao   dim ON d.dimensao_id   = dim.id
),
atual AS (
    SELECT l.d1c AS mun, p.ano, dim.d2c AS variavel, d.v::numeric AS valor_atual
    FROM ibge_sidra.dados d
    JOIN ibge_sidra.localidade l   ON d.localidade_id = l.id
    JOIN ibge_sidra.periodo    p   ON d.periodo_id    = p.id
    JOIN ibge_sidra.dimensao   dim ON d.dimensao_id   = dim.id
    WHERE d.tabela_sidra_id = '5938'
      AND d.ativo = TRUE
)
SELECT
    o.mun, o.ano, o.variavel, o.valor_2019, a.valor_atual,
    (a.valor_atual - o.valor_2019) / NULLIF(o.valor_2019, 0) AS variacao_pct
FROM original o
JOIN atual a USING (mun, ano, variavel)
WHERE o.valor_2019 IS DISTINCT FROM a.valor_atual
ORDER BY ABS((a.valor_atual - o.valor_2019) / NULLIF(o.valor_2019, 0)) DESC NULLS LAST
LIMIT 20;
```

O resultado mostra exatamente onde a revisão do IBGE impactou — útil para nota técnica, errata, ou apêndice.

## O que está acontecendo

- **Manifesto SHA-256** prova que o arquivo bruto de 2019 é exatamente o que alimentou a análise. Não é fé — é hash.
- **Uma versão por arquivo no warehouse** preserva todas as revisões. `ibge_sidra.versao.modificacao` registra quando o IBGE publicou cada período; a observação `ativo` é a que vale hoje.
- **`dados_em(data, tabela)`** é o "tempo de viagem": roda qualquer query como ela rodaria naquela data, com a mesma regra do `ativo` aplicada às versões até a data. Para a data de hoje, o resultado é o de `dados WHERE ativo`.

## Pegadinhas

- **O histórico precisa estar no bruto.** O IBGE sobrescreve a série na API; o que guarda a versão de 2019 é o arquivo `@2019...` que o coletor gravou na época. Se você só começou a coletar agora, as revisões anteriores não existem para você: **guarde o bruto (todas as versões) desde já, mesmo que não precise ainda.** Com o bruto completo, `load --historico` reconstrói a história no banco quando for preciso.
- **Versão sem data não entra.** Um arquivo cujo carimbo é `@00010101` (a API não informou a modificação) fica no banco, mas `dados_em` o ignora.
- **Manifesto sem arquivo é fraco.** Guardar só o `.manifest.json` permite verificar que o arquivo original tinha aquele hash, mas você precisa de uma cópia do dado em algum lugar (Zenodo, S3, HD). O manifesto sozinho prova quem você é, não o que disse.
- **`ativo` é só "hoje".** Se você nunca recarregou depois de uma revisão, `ativo` reflete a última carga, não a última publicação do IBGE. Recarregue o bruto novo (`load ... --all`) periodicamente.

## Anexo de replicação — o que entregar ao referee

Para o apêndice metodológico do paper, anexe:

1. **`pib-municipal.json.manifest.json`** versionado no repositório do paper.
2. **A query SQL** com `dados_em(DATE 'YYYY-MM-DD', '<tabela>')` literal, sem variáveis.
3. **A versão do `quantilica-sql`** e do `ibge-sidra-fetcher` usadas (output de `uv pip show`).
4. **Um README** mostrando como subir o warehouse a partir do zero (`load --historico`) e rodar a query.

Quatro arquivos. Zero ambiguidade.

## Veja também

- [Proveniência & Manifestos](../../conceitos/proveniencia.md)
- [quantilica-sql — SIDRA](../../fundacoes/quantilica-sql.md#sidra-ibge_sidra): o modelo, a vigência e `dados_em`.
- [Pesquisador acadêmico](../perfis/pesquisador.md) — atalhos para esse perfil.
- [Princípios — Reprodutibilidade](../../conceitos/principios.md#reprodutibilidade)
