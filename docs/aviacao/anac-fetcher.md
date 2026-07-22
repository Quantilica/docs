---
title: anac-fetcher — Dados abertos da ANAC (aviação civil)
description: Catálogo declarativo para VRA (voos regulares), RAB (aeronaves registradas), ocorrências CENIPA e infraestrutura de aeródromos.
---

# Aviação Civil (ANAC)

Dados abertos da ANAC (Agência Nacional de Aviação Civil).

**anac-fetcher** descobre datasets a partir de um catálogo declarativo (sem chamadas de rede) e baixa cada um com manifesto de proveniência (`quantilica-core`), organizados por grupo.

!!! warning "Pegadinhas da fonte oficial"

    - **Sem API.** `sistemas.anac.gov.br/dadosabertos` é um índice de diretórios cru; não há endpoint consultável nem paginação — o catálogo do `anac-fetcher` hardcoda os caminhos conhecidos.
    - **Convenção de nome de arquivo varia por área.** VRA usa `VRA_{ano}{mês}.csv` sem zero à esquerda no mês (`VRA_20001.csv` = janeiro/2000); RAB usa `{AAAA-MM}.{ext}`; cada subcategoria de aeródromo tem seu próprio nome de arquivo estático.
    - **RAB histórico tem lacunas de formato.** `csv` só existe a partir de 2024-09; meses anteriores só têm `json`/`xls`. Um mês (2019-05) não existe em formato nenhum.
    - **Dados recentes de VRA podem não estar publicados ainda.** A ANAC publica com atraso de 1-2 meses; o catálogo gera entradas até o mês corrente, e falhas de download de meses ainda não publicados não interrompem a sincronização.
    - **Grupos grandes geram muitos arquivos pequenos.** `rab` sozinho tem ~250 entradas no histórico mensal; `sync` já aplica `--sleeptime 0.3` (segundos) entre downloads por padrão, como cortesia ao servidor.

## Instalação

```bash
pip install anac-fetcher
```

**Requisitos:** Python 3.12+

## CLI

```text
anac-fetcher <command> [args]

Comandos:
  sync [GRUPOS...] [-o DIR] [--dry-run] [--verbose]
        Sincronizar datasets. Sem GRUPOS, baixa todos.
  discover [--verbose]
        Listar todos os datasets do catálogo, sem baixar.
```

`DIR` padrão é `/data/anac`.

### Exemplos

```bash
# Baixar todos os grupos
anac-fetcher sync

# Baixar VRA e RAB apenas
anac-fetcher sync vra rab -o ./dados/anac

# Baixar todos os grupos de aeródromos de uma vez
anac-fetcher sync aerodromos

# Listar sem baixar
anac-fetcher sync --dry-run

# Listar todo o catálogo
anac-fetcher discover
```

### Integração com `quantilica-cli`

```bash
quantilica anac sync
quantilica anac discover
```

## API Python

```python
from anac_fetcher.catalog import list_datasets

for entry in list_datasets(group="vra"):
    print(entry["id"], entry["url"])
```

## Datasets

| Grupo | Descrição | Cobertura |
|---|---|---|
| `vra` | Voo Regular Ativo — voos, atrasos, cancelamentos | Mensal, 2000–presente |
| `rab` | Registro Aeronáutico Brasileiro — cadastro de aeronaves | Snapshot atual + histórico mensal desde 2017-01 |
| `ocorrencias` | Ocorrências Aeronáuticas (CENIPA) | Tabela consolidada, atualizada diariamente |
| `aerodromos` | Infraestrutura de aeródromos (13 subgrupos: pistas, pátios, posições de estacionamento, helipontos, PZR, planos diretores, etc.) | Snapshot atual por subgrupo |

Execute `anac-fetcher discover` para a lista completa com URLs.

## Layout em Disco

```
/data/anac/
├── voo-regular-ativo/vra_2024-03@20240401.csv
├── registro-aeronautico-brasileiro/rab-atual-csv@20260721.csv
├── ocorrencias-cenipa/ocorrencias-csv@20260721.csv
└── aerodromos-lista-publicos/aero-lista-publicos-lista-csv@20260715.csv
```

## Fonte de Dados

[Portal de Dados Abertos da ANAC](https://www.gov.br/anac/pt-br/acesso-a-informacao/dados-abertos) — arquivos servidos por [sistemas.anac.gov.br/dadosabertos](https://sistemas.anac.gov.br/dadosabertos/).

## Saiba Mais

- **[Arquitetura do Ecossistema](../concepts/arquitetura.md)** — Design do sistema
