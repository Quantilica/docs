---
title: Cientista de dados de saúde pública — caminho rápido na Quantilica
description: Microdados do DATASUS, denominadores populacionais e estudos epidemiológicos. As ferramentas para quem trabalha SUS, SIM, SINASC, SIH.
---

# Cientista de dados de saúde pública

Você trabalha com microdados do SUS — mortalidade (SIM), nascimentos (SINASC), internações (SIH), atenção ambulatorial (SIA), cadastro de estabelecimentos (CNES). Sua rotina envolve baixar GBs de `.dbc`, juntar com denominadores populacionais, e produzir indicadores reproduzíveis.

## Suas três dores

| Dor | A ferramenta |
|---|---|
| 320+ GB de microdados em FTP legado que cai três vezes por semana | **[`datasus-fetcher`](../saude/datasus-fetcher.md)** |
| Denominadores populacionais por município, ano, faixa etária | **[`sidra-fetcher`](../ibge/sidra-fetcher.md)** (Censo, Estimativas) |
| Auditar exatamente qual versão do dado alimentou seu paper | **[Proveniência & Manifestos](../concepts/proveniencia.md)** |

## Por onde começar

1. **5 minutos:** baixe o SIH-RD para SP nos últimos 3 anos via [Quickstart aba Saúde](../quickstart.md).
2. **15 minutos:** liste todos os 113 datasets do DATASUS com `datasus-fetcher list`. Veja a estrutura antes de comprometer disco.
3. **30 minutos:** combine mortalidade do SIM com população do SIDRA para taxa por 100k habitantes — receita em [Mortalidade infantil × SUS](../cookbook/mortalidade-sus.md).

### SIH-RD para SP em 3 linhas de CLI

```bash
# Listar datasets disponíveis
datasus-fetcher list

# Baixar internações hospitalares para SP, 2022–2023
datasus-fetcher sync sih-rd --regions sp --start 2022-01 --end 2023-12 -o /data/datasus

# Converter .dbc para Parquet (leitura 10× mais rápida)
datasus-fetcher convert sih-rd -o /data/datasus/parquet
```

```python
# Leitura após conversão
import polars as pl
df = pl.read_parquet("/data/datasus/parquet/sih-rd/**/*.parquet")
print(df.shape)  # (linhas, colunas)
```

## O conceito que importa para você

> **[Reprodutibilidade](../concepts/principios.md#reprodutibilidade)** — o DATASUS republica arquivos antigos quando há correção, frequentemente sem mudar o nome. A coluna `archive/` do `datasus-fetcher` e o manifesto SHA-256 permitem provar com qual versão exata você trabalhou.

## Padrões que economizam tempo

- **Filtre cedo.** Use `--regions sp rj mg` e `--start 2020-01 --end 2023-12` antes de qualquer download massivo. 320 GB começam pequenos quando você sabe o recorte.
- **`.dbc` precisa de leitor próprio.** Use `pyreaddbc` ou converta para Parquet via [`quantilica-analytics`](../fundacoes/quantilica-analytics.md). `pd.read_csv` não abre.
- **Baixe dicionários junto.** `datasus-fetcher sync --docs` traz os PDFs de descrição dos campos — sem eles, códigos como `RACACOR=4` ou `CAUSABAS=I64` são opacos.
- **Use `--dry-run` antes do download real.** Mostra tamanho total e número de arquivos. Evita surpresa de 50 GB.

## Caminho de aprofundamento

- [`datasus-fetcher` — referência completa de CLI](../saude/datasus-fetcher.md)
- [Princípios — Resiliência](../concepts/principios.md#resiliência) — entenda como retry e versionamento funcionam.
- [Cookbook](../cookbook/index.md) — receitas que cruzam saúde com outras fontes.
