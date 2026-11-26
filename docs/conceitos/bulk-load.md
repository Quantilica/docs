---
title: Bulk Load & Versionamento de Revisões
description: Como o quantilica-sql (e os legados sidra-sql e bcb-sgs-sql) ingere milhões de linhas via COPY e preserva o histórico de revisões oficiais.
---

# Bulk Load & Versionamento de Revisões

Os data warehouses do ecossistema — o **[quantilica-sql](../fundacoes/quantilica-sql.md)** (IBGE
SIDRA, BCB SGS e as demais fontes) e os pacotes legados que ele substitui,
**[sidra-sql](../fontes/ibge/sidra-sql.md)** e **[bcb-sgs-sql](../fontes/bcb/bcb-sgs-sql.md)** —
compartilham dois mecanismos de infraestrutura. Esta página explica *como funcionam*; as
páginas de cada pacote mostram *como usá-los*. O que cada um faz no versionamento está
na tabela [abaixo](#versionamento-de-revisões).

1. **Ingestão em massa** sem estourar RAM, via `COPY FROM STDIN` + tabela de staging.
2. **Versionamento de revisões**: as fontes oficiais revisam dados publicados sem aviso, e
   o warehouse nunca sobrescreve — acrescenta a nova versão e deixa a antiga como história.

Ambos materializam os princípios de [Resiliência e Reprodutibilidade](principios.md):
um snapshot histórico pode ser reproduzido exatamente, mesmo após correções da fonte.

---

## Ingestão em massa via COPY

### O problema: `INSERT` linha-a-linha

A abordagem ingênua — inserir uma linha por vez via ORM — não escala para os volumes do
SIDRA (dezenas de milhões de linhas) ou de séries diárias longas do SGS:

```python
# ❌ Inserção linha-por-linha (abordagem ingênua)
for row in data_generator():
    conn.execute(insert(dados).values(...))
conn.commit()

# Tempo: horas a dias para 10M linhas
# RAM:   explode (mantém tudo em memória)
# I/O:   pior caso (milhões de round-trips)
```

### A solução: `COPY FROM STDIN` + staging

O protocolo binário nativo do PostgreSQL transmite milhões de registros para uma **tabela
de staging temporária**, e a promoção para a tabela definitiva é atômica:

- **`COPY FROM STDIN`** — túnel único, protocolo binário, streaming (não tudo-em-memória).
- **Tabela de staging** (`_staging_dados` / `_staging_series_data`) — operações atômicas.
- **Upsert idempotente** — `ON CONFLICT DO NOTHING` / detecção-de-mudança deduplica.

**Performance típica** (hardware comum, 8 núcleos): ~400k linhas/s; 10M linhas em segundos,
contra horas com `INSERT` tradicional.

### Dois passes vs. passe único

A forma do modelo de dados decide quantos passes a carga precisa:

=== "SIDRA — dois passes (star schema)"

    O modelo dimensional do SIDRA tem chaves estrangeiras (localidade, período, dimensão)
    que precisam ser resolvidas **antes** da carga dos fatos. O diagrama abaixo é o do
    `sidra-sql`; o `quantilica-sql` segue a mesma ideia por arquivo: resolve as dimensões em
    memória, grava as observações por `COPY` e refaz a vigência das células afetadas, tudo
    na mesma transação do arquivo (e do registro no ledger).

    ```mermaid
    graph TD
        subgraph P1 [Pass 1: Resolver Dimensões]
            P1a[Carregar localidade em memória]
            P1b[Carregar dimensao em memória]
            P1c[Mapear códigos string → IDs FK numéricos]
        end
        subgraph P2 [Pass 2: Stream em Lote para Staging]
            P2a[Abrir túnel PostgreSQL COPY]
            P2b[Escrever linhas binárias para staging]
            P2c[UPSERT Atômico: ON CONFLICT DO NOTHING]
        end
        subgraph P3 [Pass 3: Validar & Promover]
            P3a[Validação de integridade referencial]
            P3b[Trocar staging → produção atomicamente]
        end
        P1 --> P2
        P2 --> P3
    ```

=== "SGS — passe único (série plana)"

    A série temporal do SGS é plana `(série, data, valor)` — sem dimensões com FK a
    resolver — então não há o "Pass 1".

    ```mermaid
    graph TD
        S1[COPY observações → _staging_series_data] --> S2[_ENSURE_SERIES: stubs de catálogo]
        S2 --> S3[_DEACTIVATE: ativa anterior vira FALSE se valor difere]
        S3 --> S4[_INSERT: linhas novas/alteradas viram ativa]
    ```

---

## Versionamento de revisões

Tanto o IBGE quanto o BCB **revisam dados históricos sem aviso**. Sobrescrever o valor
antigo destruiria a reprodutibilidade de uma pesquisa ou de um modelo treinado num snapshot.
A solução do ecossistema: **nunca deletar** — inserir a nova versão e marcar a anterior como
inativa, preservando a trilha completa.

Cada warehouse aplica a variante adequada à sua fonte:

| | `sidra-sql` (legado, SIDRA) | `quantilica-sql` (SIDRA) | `bcb-sgs-sql` e `quantilica-sql` (SGS) |
|---|---|---|---|
| Técnica | SCD Type II por linha | Versão por arquivo, vigência derivada por célula | Soft-versioning por detecção-de-mudança |
| Colunas | `ativo`, `modificacao` na linha | `ativo` na observação; `modificacao`, `sha256` e `consulta` na `versao` | `ativo`, `loaded_at` |
| "Verdade atual" | `WHERE ativo = TRUE` | `WHERE ativo = TRUE` | `WHERE ativo = TRUE` |
| Trilha de revisões | `ORDER BY modificacao` | uma `versao` por arquivo, nada apagado | `ORDER BY loaded_at` |
| Consulta no tempo | `modificacao <= D` com `ativo = TRUE` (incorreta: descarta o que foi revisado depois de D) | `dados_em(D, tabela)` | não há (só `loaded_at`) |
| Tabela de auditoria | nenhuma (na própria fato) | `versao` e o ledger `arquivo_carregado` (`sha256`) | o ledger `arquivo_carregado` |

No SIDRA do `quantilica-sql`, cada arquivo coletado é uma versão e só uma observação por célula é
`ativo`: a da versão mais recente da consulta mais recente que a cobre. O estado ativo não
depende da ordem de carga. O detalhe está em [quantilica-sql — SIDRA](../fundacoes/quantilica-sql.md#sidra-ibge_sidra).

### A ordem importa: desativar antes de inserir

Quando o valor de uma observação muda, a carga **desativa a linha anterior antes** de
inserir a revisão. Isso garante que a chave revisada não tenha linha ativa no instante do
`INSERT`, satisfazendo o índice único parcial que admite no máximo uma linha ativa por chave:

```sql
-- 1. Desativar a versão anterior (só se o valor diferir)
UPDATE series_data SET ativo = FALSE
WHERE series_id = 433 AND date = '2020-01-01'
  AND ativo = TRUE AND value IS DISTINCT FROM 0.25;

-- 2. Inserir a revisão como nova linha ativa
INSERT INTO series_data (series_id, date, value, loaded_at, ativo)
VALUES (433, '2020-01-01', 0.25, now(), TRUE);
```

Recarregar um valor idêntico é um **no-op**: nada é desativado nem inserido (zero churn),
o que torna as recargas idempotentes.

### Reproduzir um snapshot histórico

Como nenhuma versão é apagada, é possível reconstruir o banco como ele estava em qualquer
momento do passado — a base do padrão de [Proveniência & Manifestos](proveniencia.md) e da
receita [Time Travel](../guias/receitas/time-travel.md).

No SIDRA do `quantilica-sql`, a função `dados_em` faz a consulta (a versão mais recente com
`modificacao` até a data, ativa ou não):

```sql
-- O dado como existia em 2024-06-01
SELECT * FROM ibge_sidra.dados_em('2024-06-01', '5938');
```

!!! warning "`modificacao <= D` com `ativo = TRUE` não reproduz o passado"

    `ativo` marca a versão vigente hoje. Uma célula revisada depois de `D` tem a versão que
    valia em `D` inativa, e o filtro a descarta (a consulta volta sem a célula, em vez de
    devolver o valor antigo). Foi a receita do `sidra-sql`; use `dados_em`.

No SGS (`series_data`) o que existe é `loaded_at`: `WHERE ativo` dá a verdade atual, e
as linhas inativas, ordenadas por `loaded_at`, são a trilha de revisões.

---

## Onde isto aparece

- **[quantilica-sql](../fundacoes/quantilica-sql.md)** — versões por arquivo e `dados_em` para o star schema do SIDRA; soft-versioning para as séries do SGS.
- **[sidra-sql](../fontes/ibge/sidra-sql.md)** (legado) — dois passes + SCD Type II para o star schema do SIDRA.
- **[bcb-sgs-sql](../fontes/bcb/bcb-sgs-sql.md)** (legado) — passe único + soft-versioning para as séries do SGS.
- **[Proveniência & Manifestos](proveniencia.md)** — o lado de coleta da mesma garantia de reprodutibilidade.
