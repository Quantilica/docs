---
title: anac-fetcher — Dados abertos da ANAC (aviação civil)
description: Catálogo declarativo para VRA (voos regulares), RAB (aeronaves registradas), ocorrências CENIPA e infraestrutura de aeródromos.
---

# Aviação Civil (ANAC)

Dados abertos da ANAC (Agência Nacional de Aviação Civil).

**anac-fetcher** descobre datasets a partir de um catálogo declarativo (sem chamadas de rede) e baixa cada um com manifesto de proveniência (`quantilica-core`), organizados por grupo.

!!! warning "Pegadinhas da fonte oficial"

    - **Sem API.** O `sistemas.anac.gov.br` é um índice de diretórios cru. O catálogo hardcoda caminhos conhecidos.
    - **Convenção de nome varia:** VRA usa `VRA_{ano}{mês}.csv` sem zero à esquerda (`VRA_20001.csv` = Jan/2000); RAB usa `{AAAA-MM}.{ext}`.
    - **Atrasos de publicação:** A ANAC publica o VRA com 1 a 2 meses de atraso; se o script tentar baixar o mês atual e der 404, ele ignora sem interromper os demais.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install anac

# Ou como biblioteca no seu projeto
uv add anac-fetcher --index https://index.quantilica.com/simple/
```

**Requisitos:** Python 3.12+

## CLI

```bash
# Baixar VRA e RAB apenas
anac-fetcher sync vra rab -o ./dados/anac

# Baixar toda infraestrutura de aeródromos de uma vez
anac-fetcher sync aerodromos

# Listar todo o catálogo
anac-fetcher discover
```

---

## Datasets Principais

| Grupo | Descrição | Cobertura |
|---|---|---|
| `vra` | Voo Regular Ativo — voos, atrasos, cancelamentos | Mensal, 2000–presente |
| `rab` | Registro Aeronáutico Brasileiro — cadastro de aeronaves | Histórico mensal desde 2017-01 |
| `ocorrencias` | Ocorrências Aeronáuticas (CENIPA) | Tabela atualizada diariamente |

### Lacunas Históricas no RAB

O histórico do **Registro Aeronáutico Brasileiro (RAB)** é turbulento. O catálogo gerencia inteligentemente esses formatos variáveis, tentando primeiro `.csv`, depois `.json` e `.xls`:

| Período | Extensão de Arquivo Disponível |
|---|---|
| **Antes de 2019-05** | Apenas `json` ou `xls` |
| **2019-05** | 🔴 Arquivo inexistente nos servidores da ANAC |
| **Até 2024-08** | Apenas `json` ou `xls` |
| **2024-09 em diante** | `.csv` padronizado e disponibilizado |

---

## A Macro `aerodromos`

Ao invés de sincronizar bases soltas, o alias `aerodromos` resolve **14 subgrupos distintos** de infraestrutura aeroportuária brasileira. Todos tentam baixar prioritariamente CSV, caindo para JSON/XLS quando necessário. O nível de granularidade engloba:

- `aero-lista-publicos` (Lista oficial de aeródromos públicos)
- `aero-caracteristicas` (Características físicas gerais)
- `aero-pistas-pouso` (Pistas de pouso e decolagem)
- `aero-pistas-taxi` (Áreas de taxiamento)
- `aero-patio` (Dados de pátios)
- `aero-posicoes-estacionamento` (Posições de aeronaves)
- `aero-helipontos-publicos` (Helipontos públicos)
- `aero-excluidos` (Aeródromos desativados)
- `aero-seguranca` (Programas de segurança)
- `aero-lista-privados` (Aeródromos privados)
- `aero-helideck` (Helidecks off-shore / plataformas)
- `aero-heliponto-privado` (Helipontos privados)
- `aero-pzr` (Planos de Zoneamento de Ruído)
- `aero-plano-diretor` (Planos Diretores Aeroportuários Aprovados e Validados)

Basta rodar `anac-fetcher sync aerodromos` para ter a radiografia completa da infraestrutura do Brasil.

---

## Cookbook: Analisando VRA com Polars

O grupo `vra` baixa centenas de arquivos (um por mês desde 2000). Para não estourar a memória (o VRA acumula milhões de registros), o ideal é usar `polars.scan_csv`:

```python
import polars as pl

# O VRA é distribuído em CSVs separados por ponto-e-vírgula.
# Utilizamos o scan_csv para criar um LazyFrame (avaliação preguiçosa)
df_vra = pl.scan_csv(
    "data/anac/voo-regular-ativo/*.csv",
    separator=";",
    infer_schema_length=10000,
    ignore_errors=True
)

# Descobrir a companhia aérea com mais cancelamentos
cancelamentos = (
    df_vra
    .filter(pl.col("Situação Voo") == "CANCELADO")
    .group_by("Empresa Aérea")
    .agg(pl.count().alias("Total_Cancelamentos"))
    .sort("Total_Cancelamentos", descending=True)
    .collect()
)

print(cancelamentos)
```

## Saiba Mais

- **[Arquitetura do Ecossistema](../concepts/arquitetura.md)** — Design do sistema
