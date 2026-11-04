---
title: anp-fetcher — Dados abertos e estatísticos da ANP
description: Catálogo da ANP: preços de combustíveis, vendas, produção, comércio exterior, royalties, movimentação, qualidade e produção por poço.
---

# Petróleo, Gás e Biocombustíveis (ANP)

Dados abertos e estatísticos da ANP (Agência Nacional do Petróleo, Gás Natural e Biocombustíveis).

**anp-fetcher** descobre datasets a partir de um catálogo declarativo (sem chamadas de rede) e baixa cada um com manifesto de proveniência (`quantilica-core`), organizados por grupo. O catálogo tem **63 grupos** e **45 aliases**, com mais de 1.700 arquivos. Ele foi projetado para esconder toda a complexidade e instabilidade da fonte original.

!!! warning "Pegadinhas da fonte oficial (que o anp-fetcher resolve para você)"

    - **Convenção de nome de arquivo muda ao longo do tempo:** Ex.: preços mensais de diesel/GNV usam `precos-{produto}-{mm}.csv` até 2025 e `{mm}-dados-abertos-precos-{produto}.{ext}` a partir de 2026. Além disso, a partir de 2026, certos dados saem em `.xlsx` em vez de `.csv`. O fetcher tenta a extensão principal e possui URLs de fallback dinâmicas.
    - **Separador de campo mutável:** Royalties por união/estado/município têm três eras de nomenclatura (`royalties_uniao_2018.csv` → `royalties-uniao-2019.csv`).
    - **Royalties e participação especial não têm código IBGE:** os CSVs reais não trazem `codigo_ibge` — o município vem só por nome, em minúsculo e sem acento. As colunas `competencia` e `caixa` são datas seriais do Excel (número de dias), não texto. A junção por código de município não existe na fonte.
    - **A camada de poços do BDEP não é coletada:** os endereços `bdep.gov.br`, `www.bdep.gov.br`, `bdep.anp.gov.br`, `geo.anp.gov.br` e `sigep.anp.gov.br` não resolvem DNS, e a página de shapefiles da ANP (`/dados-tecnicos/shapefile-de-dados`) publica só rodadas/blocos (`brc`, `op`, `a3`, `a4`), sem camada de poços. Os poços públicos seguem vindo do grupo `acervo-dados-tecnicos` (`pocos-publicos-<ano>.csv`); `situacao-pocos` traz `Latitude_da_base`/`Longitude_da_base` em graus (`-18:22:40,186`), mas sem datum declarado — assumir EPSG:4674 seria suposição.
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
quantilica anp <command> [args]

Comandos:
  sync [GRUPOS...] [-o DIR] [--dry-run] [--verbose]
        Sincronizar datasets. Sem GRUPOS, baixa todos.
  check [GRUPOS...] [--json | --out ARQ]
        Comparar disco e remoto sem baixar; grava o plano que o
        `sync --from-plan` consome.
  list
        Listar todos os datasets do catálogo, sem baixar.
  convert [-i DIR] [--lake DIR] [--dataset DS] [--force]
        Converter o acervo bruto para o lake Hive (requer o extra analysis).
  pipeline [GRUPOS...] [-o DIR] [--lake DIR]
        Baixar e converter em uma só execução.
```

`DIR` padrão é `/data/anp`.

### Exemplos

```bash
# Baixar todos os grupos
quantilica anp sync

# Dados estatísticos específicos
quantilica anp sync ie pp -o ./dados/anp

# Todos os grupos de preços de combustíveis (SHPC) de uma vez
quantilica anp sync shpc-ca shpc-glp shpc-diesel-gnv shpc-gasolina-etanol shpc-glp-mensal shpc-4s

# Listar sem baixar
quantilica anp sync --dry-run
```

## Fases dos Dados: Abertos vs Estatísticos

O catálogo unifica duas fontes principais da ANP:

1. **Dados Estatísticos (Fase 1):** Consolidados em planilhas (`XLS/XLSX`). Trazem totalizadores agregados (ex: `ie` para Importações/Exportações, `pp` para Processamento). Útil para visões macro e anuários.
2. **Dados Abertos:** Microdados granulares (geralmente em `.csv` ou `.zip`). Trazem os registros linha a linha (ex: vendas por município, preços por posto). Essencial para modelos de machine learning e painéis interativos.

---

## Preços de Combustíveis (`shpc-*`)

O Sistema de Levantamento de Preços (SHPC) é vasto e se divide em seis grupos. Não existe um macro-alias `shpc`: informe os grupos que precisar. O alias `precos-combustiveis` cobre apenas o `shpc-ca`.

Os seis grupos da base de preços, desde 2004:
- `shpc-ca`: Combustíveis automotivos (Semestral, 2004–2025)
- `shpc-glp`: GLP P13 (Semestral, 2004–2025)
- `shpc-diesel-gnv`: Diesel e GNV (Mensal, 2023–hoje)
- `shpc-gasolina-etanol`: Gasolina e Etanol (Mensal, 2023–hoje)
- `shpc-glp-mensal`: GLP (Mensal, 2023–hoje)
- `shpc-4s`: Últimas 4 semanas (Snapshot dinâmico)

### Cookbook: Lendo o histórico do SHPC em Polars

Uma vez que você baixou os grupos `shpc-*`, você terá dezenas de zips e csvs históricos. Para carregar tudo eficientemente:

```python
import polars as pl
from pathlib import Path

# Como a ANP altera encodings e separadores, uma leitura unificada
# robusta em LazyFrames usa inferência agressiva e preenchimento de nulos.
# (arquivos antigos do `shpc-ca` vêm em .zip e ficam fora deste glob)
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

O catálogo tem **63 grupos** e **45 aliases**; as tabelas abaixo cobrem as famílias mais usadas. Execute `quantilica anp list` para a lista completa, com todas as entradas e URLs.

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
| `royalties` | Participações governamentais (royalties e participação especial) e preços de referência |

## Participações governamentais e preços de referência

O grupo `royalties` reúne arquivos de esquemas diferentes: royalties da união, do estado e do município; participação especial da união, do estado, do município e do campo; e os preços de referência do gás natural e do petróleo. O conversor do lake usa uma tabela de roteamento explícita, pelo `base_id` do catálogo (nunca por trecho do nome), e separa cada um em seu próprio dataset:

| `base_id` | dataset no lake |
|---|---|
| `royalties-uniao` | `royalties_uniao` |
| `royalties-estado` | `royalties_estado` |
| `royalties-municipio` | `royalties_municipio` |
| `pe-uniao`, `pe-estado`, `pe-municipio`, `pe-campo` | `participacoes_especiais` |
| `preco-ref-gn` | `preco_referencia_gn` |
| `preco-ref-petroleo` | `preco_referencia_petroleo` |

- Os quatro recortes de participação especial convivem no mesmo dataset: a coluna **`recorte`** (`uniao`, `estado`, `municipio`, `campo`) os separa, porque os esquemas diferem.
- `base_id` fora da tabela fica no dataset do grupo, sem adivinhação.
- Em `--dataset`, os nomes de dataset (`royalties_uniao`, `royalties_estado`, `royalties_municipio`, `participacoes_especiais`, `preco_referencia_gn`, `preco_referencia_petroleo`) são aceitos como aliases do grupo `royalties`: cada um converte apenas o próprio dataset e `--dataset royalties` converte todos de uma vez.
- **Reconversão:** os parquets `preco-ref-*` gerados por versão anterior estão em `royalties/` — remova-os de lá e reconverta com `--force`; `participacoes_especiais` também pede `--force` para ganhar a coluna `recorte`.

## Saiba Mais

- **[Arquitetura do Ecossistema](../../conceitos/arquitetura.md)** — Design do sistema
