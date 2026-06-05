---
title: Bulk Load & Versionamento de Revisões
description: Como os data warehouses do ecossistema (sidra-sql, bcb-sgs-sql) ingerem milhões de linhas via COPY FROM STDIN e preservam o histórico de revisões oficiais sem sobrescrever dados.
---

# Bulk Load & Versionamento de Revisões

Os data warehouses do ecossistema — **[sidra-sql](../ibge/sidra-sql.md)** (IBGE) e
**[bcb-sgs-sql](../bcb/bcb-sgs-sql.md)** (BCB SGS) — compartilham dois mecanismos de
infraestrutura. Esta página explica *como funcionam*; as páginas de cada pacote mostram
*como usá-los*.

1. **Ingestão em massa** sem estourar RAM, via `COPY FROM STDIN` + tabela de staging.
2. **Versionamento de revisões**: as fontes oficiais revisam dados publicados sem aviso, e
   o warehouse nunca sobrescreve — acrescenta a nova versão e marca a antiga como inativa.

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
    que precisam ser resolvidas **antes** da carga dos fatos.

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

| | `sidra-sql` (SIDRA) | `bcb-sgs-sql` (SGS) |
|---|---|---|
| Técnica | SCD Type II | Soft-versioning por detecção-de-mudança |
| Colunas | `ativo`, `modificacao` | `ativo`, `loaded_at` |
| "Verdade atual" | `WHERE ativo = TRUE` | `WHERE ativo = TRUE` |
| Trilha de revisões | `ORDER BY modificacao` | `ORDER BY loaded_at` |
| Tabela de auditoria | nenhuma (na própria fato) | nenhuma (na própria fato) |

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

Como nenhuma versão é apagada, filtrar pela data de revisão reconstrói o banco como ele
estava em qualquer momento do passado — a base do padrão de [Proveniência &
Manifestos](proveniencia.md) e da receita [Time Travel](../cookbook/time-travel.md):

```sql
-- O dado como existia em 2024-06-01
SELECT * FROM ibge_sidra.dados
WHERE modificacao <= '2024-06-01' AND ativo = TRUE;
```

---

## Onde isto aparece

- **[sidra-sql](../ibge/sidra-sql.md)** — dois passes + SCD Type II para o star schema do SIDRA.
- **[bcb-sgs-sql](../bcb/bcb-sgs-sql.md)** — passe único + soft-versioning para as séries do SGS.
- **[Proveniência & Manifestos](proveniencia.md)** — o lado de coleta da mesma garantia de reprodutibilidade.
