---
title: anp-fetcher — Dados abertos e estatísticos da ANP
description: Catálogo declarativo cobrindo preços de combustíveis (SHPC), vendas e produção, comércio exterior, royalties, movimentação e qualidade de combustíveis, produção por poço.
---

# Petróleo, Gás e Biocombustíveis (ANP)

Dados abertos e estatísticos da ANP (Agência Nacional do Petróleo, Gás Natural e Biocombustíveis).

**anp-fetcher** descobre datasets a partir de um catálogo declarativo (sem chamadas de rede) e baixa cada um com manifesto de proveniência (`quantilica-core`), organizados por grupo.

!!! warning "Pegadinhas da fonte oficial"

    - **Convenção de nome de arquivo muda ao longo do tempo, dentro do mesmo dataset.** Ex.: preços mensais de diesel/GNV usam `precos-{produto}-{mm}.csv` até 2025 e `{mm}-dados-abertos-precos-{produto}.{ext}` a partir de 2026 (e abril/2026 sai em `.xlsx`, não `.csv`). O catálogo hardcoda cada exceção conhecida — ver `anp_fetcher/catalog_dados_abertos.py`.
    - **Separador de campo muda entre `_`, `-` e nenhum.** Royalties por união/estado/município têm três eras de nomenclatura (`royalties_uniao_2018.csv` → `royalties-uniao-2019.csv`, com um ano isolado em subpasta própria).
    - **Sem API.** Assim como no `anac-fetcher`, os dados-abertos da ANP são arquivos estáticos servidos a partir de páginas de conteúdo do `gov.br/anp`; não há endpoint consultável.

## Instalação

```bash
pip install anp-fetcher
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

# Listar todo o catálogo
anp-fetcher discover
```

### Integração com `quantilica-cli`

```bash
quantilica anp sync
quantilica anp discover
```

## API Python

```python
from anp_fetcher.catalog import list_datasets

for entry in list_datasets(group="ie"):
    print(entry["id"], entry["url"])
```

## Datasets

### Dados Estatísticos (XLS/XLSX)

| Grupo | Descrição |
|---|---|
| `ie` | Importações e Exportações |
| `pp` | Processamento de Petróleo |
| `pb` | Produção de Biocombustíveis |
| `ppg` | Produção de Petróleo e Gás Natural |
| `vdpb` | Vendas de Derivados de Petróleo e Biocombustíveis |

### Dados Abertos — SHPC (Sistema de Levantamento de Preços)

Agrupáveis via o alias `shpc`.

| Grupo | Descrição | Cobertura |
|---|---|---|
| `shpc-ca` | Preços de combustíveis automotivos | Semestral, 2004–presente |
| `shpc-glp` | Preços de GLP P13 | Semestral, 2004–presente |
| `shpc-diesel-gnv` | Preços de diesel (S-500, S-10) + GNV | Mensal, 2023–presente |
| `shpc-gasolina-etanol` | Preços de gasolina C + etanol hidratado | Mensal, 2023–presente |
| `shpc-glp-mensal` | Preços de GLP P13 | Mensal, 2023–presente |
| `shpc-4s` | Preços das últimas 4 semanas | Snapshot atual |

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
| `comercializacao-gn` | Comercialização de gás natural (distribuidoras, produtores, comercializadores) |
| `movimentacao-terminais` | Movimentação de terminais aquaviários de derivados |
| `armazenagem-terminais` | Capacidade de armazenagem de terminais |
| `movimentacao-gn` | Movimentação de gás natural em gasodutos de transporte |
| `movimentacao-derivados` | Logística de derivados (asfalto, aviação, GLP, lubrificantes, TRR, etc.) |
| `tancagem` | Tancagem do abastecimento nacional de combustíveis |
| `pmqc` | Monitoramento da qualidade dos combustíveis |
| `incidentes` | Incidentes de segurança operacional em E&P |
| `rodadas` | Rodadas de licitações (blocos, ofertas vencedoras, cessão de contratos) |
| `concessionarios` | Relação de concessionários e país de origem |
| `revendedores` / `revendas-glp` | Cadastro de revendedores varejistas / revendas de GLP |
| `registro-lubrificantes` / `pml` | Registro e monitoramento de qualidade de lubrificantes |
| `fiscalizacao` | Ações de fiscalização do abastecimento |
| `royalties` | Participações governamentais (royalties, participação especial, preços de referência) |

Execute `anp-fetcher discover` para a lista completa com URLs.

## Layout em Disco

```
/data/anp/
├── importacoes-exportacoes/ie-m3@20260529.xlsx
├── shpc-combustiveis-automotivos/shpc-ca_2024-01@20260601.zip
├── vendas-abertos/vdpb-a-combustiveis-m3@20260715.csv
└── participacoes-governamentais/royalties-uniao_2020@20260629.csv
```

## Fonte de Dados

[Portal de Dados Abertos da ANP](https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos).

## Saiba Mais

- **[Arquitetura do Ecossistema](../concepts/arquitetura.md)** — Design do sistema
