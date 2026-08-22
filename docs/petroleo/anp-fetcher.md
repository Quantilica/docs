---
title: anp-fetcher — Dados abertos e estatísticos da ANP
description: Catálogo declarativo cobrindo preços de combustíveis (SHPC), vendas e produção, comércio exterior, royalties, movimentação e qualidade de combustíveis, produção por poço.
---

# Petróleo, Gás e Biocombustíveis (ANP)

Dados abertos e estatísticos da ANP (Agência Nacional do Petróleo, Gás Natural e Biocombustíveis).

**anp-fetcher** descobre datasets a partir de um catálogo declarativo (sem chamadas de rede) e baixa cada um com manifesto de proveniência (`quantilica-core`), organizados por grupo. Ele foi projetado para esconder toda a complexidade e instabilidade da fonte original.

!!! warning "Pegadinhas da fonte oficial (que o anp-fetcher resolve para você)"

    - **Convenção de nome de arquivo muda ao longo do tempo:** Ex.: preços mensais de diesel/GNV usam `precos-{produto}-{mm}.csv` até 2025 e `{mm}-dados-abertos-precos-{produto}.{ext}` a partir de 2026. Além disso, a partir de 2026, certos dados saem em `.xlsx` em vez de `.csv`. O fetcher tenta a extensão principal e possui URLs de fallback dinâmicas.
    - **Separador de campo mutável:** Royalties por união/estado/município têm três eras de nomenclatura (`royalties_uniao_2018.csv` → `royalties-uniao-2019.csv`).
    - **Sem API:** Os dados são arquivos estáticos servidos a partir de páginas do `gov.br/anp`; não há endpoint consultável. O catálogo da Quantilica resolve isso com hardcoding inteligente e lógica de predição temporal.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install anp

# Ou como biblioteca no seu projeto
uv add anp-fetcher --index https://index.quantilica.com/simple/
```

**Requisitos:** Python 3.12+

## CLI

```text
anp-fetcher <command> [args]

Comandos:
  sync [GRUPOS...] [-o DIR] [--dry-run] [--verbose]
        Sincronizar datasets. Sem GRUPOS, baixa todos.
  discover [--verbose]
        Listar todos os datasets do catálogo, sem baixar.
```

`DIR` padrão é `/data/anp`.

### Exemplos

```bash
# Baixar todos os grupos
anp-fetcher sync

# Dados estatísticos específicos
anp-fetcher sync ie pp -o ./dados/anp

# Todos os grupos de preços de combustíveis (SHPC) de uma vez
anp-fetcher sync shpc

# Listar sem baixar
anp-fetcher sync --dry-run
```

## Fases dos Dados: Abertos vs Estatísticos

O catálogo unifica duas fontes principais da ANP:

1. **Dados Estatísticos (Fase 1):** Consolidados em planilhas (`XLS/XLSX`). Trazem totalizadores agregados (ex: `ie` para Importações/Exportações, `pp` para Processamento). Útil para visões macro e anuários.
2. **Dados Abertos (Fases 2 e 3a):** Microdados granulares (geralmente em `.csv` ou `.zip`). Trazem os registros linha a linha (ex: vendas por município, preços por posto). Essencial para modelos de machine learning e painéis interativos.

---

## O Macro-Alias `shpc` (Preços de Combustíveis)

O Sistema de Levantamento de Preços (SHPC) é vasto. Em vez de baixar subgrupos um por um, o `anp-fetcher` oferece o macro-alias `shpc`. 

Ao executar `anp-fetcher sync shpc`, o fetcher expande e coleta automaticamente **seis** verticais da base de preços desde 2004:
- `shpc-ca`: Combustíveis automotivos (Semestral, 2004–2025)
- `shpc-glp`: GLP P13 (Semestral, 2004–2025)
- `shpc-diesel-gnv`: Diesel e GNV (Mensal, 2023–hoje)
- `shpc-gasolina-etanol`: Gasolina e Etanol (Mensal, 2023–hoje)
- `shpc-glp-mensal`: GLP (Mensal, 2023–hoje)
- `shpc-4s`: Últimas 4 semanas (Snapshot dinâmico)

### Cookbook: Lendo o histórico do SHPC em Polars

Uma vez que você baixou toda a base com `anp-fetcher sync shpc`, você terá dezenas de zips e csvs históricos. Para carregar tudo eficientemente:

```python
import polars as pl
from pathlib import Path

# Como a ANP altera encodings e separadores, uma leitura unificada
# robusta em LazyFrames usa inferência agressiva e preenchimento de nulos.
df_lazy = pl.scan_csv(
    "data/anp/shpc-*/*.csv", 
    separator=";", 
    infer_schema_length=0, # Ler tudo como string primeiro para evitar erros de casting
    ignore_errors=True
)

# Filtre apenas o que precisa antes de coletar para a RAM
gasolina_sp = (
    df_lazy
    .filter(pl.col("Estado - Sigla") == "SP")
    .filter(pl.col("Produto") == "GASOLINA")
    .collect()
)
```

---

## Datasets

### Dados Estatísticos (XLS/XLSX)

| Grupo | Descrição |
|---|---|
| `ie` | Importações e Exportações |
| `pp` | Processamento de Petróleo |
| `pb` | Produção de Biocombustíveis |
| `ppg` | Produção de Petróleo e Gás Natural |
| `vdpb` | Vendas de Derivados de Petróleo e Biocombustíveis |

### Dados Abertos — Vendas, Produção e Comércio Exterior

| Grupo | Descrição |
|---|---|
| `vdpb-abertos` | Vendas de derivados e biocombustíveis (por produto, segmento e município) |
| `pp-abertos` | Processamento de petróleo e produção de derivados |
| `producao-el` | Produção de petróleo/LGN/gás natural por estado e localização |
| `pb-abertos` | Produção de biocombustíveis (biodiesel, etanol) |
| `ie-abertos` | Importações e exportações (petróleo, gás natural, derivados, etanol) |
| `producao-poco-abertos` | Produção de petróleo e gás natural por poço |
| `producao-fdp-mar` / `producao-fdp-terra` | Produção por campo — mar / terra |

### Dados Abertos — Logística, Infraestrutura e Regulação

| Grupo | Descrição |
|---|---|
| `comercializacao-gn` | Comercialização de gás natural |
| `movimentacao-terminais` | Movimentação de terminais aquaviários |
| `armazenagem-terminais` | Capacidade de armazenagem de terminais |
| `tancagem` | Tancagem do abastecimento nacional de combustíveis |
| `pmqc` | Monitoramento da qualidade dos combustíveis |
| `incidentes` | Incidentes de segurança operacional em E&P |
| `rodadas` | Rodadas de licitações |
| `concessionarios` | Relação de concessionários e país de origem |
| `revendedores` / `revendas-glp` | Cadastro de revendedores varejistas |
| `royalties` | Participações governamentais (royalties, participação especial) |

Execute `anp-fetcher discover` para a lista completa.

## Saiba Mais

- **[Arquitetura do Ecossistema](../concepts/arquitetura.md)** — Design do sistema
