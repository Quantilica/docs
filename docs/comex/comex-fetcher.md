---
title: comex-fetcher — Comércio exterior do Brasil via Siscomex
description: Downloader resiliente para os arquivos GB do Siscomex (importação e exportação). Idempotência temporal, streaming chunked, tolerância a SSL ruim.
---

# Comércio Exterior (Comex)

Dados de importação e exportação brasileira extraídos do Siscomex (Sistema Integrado de Comércio Exterior).

**comex-fetcher** é um agente de extração resiliente de rede — projetado especificamente para lidar com a infraestrutura governamental legada, superando instabilidades através de downloads idempotentes e eficiência via *chunk streaming*.

!!! warning "Pegadinhas da fonte oficial"

    - **Arquivos em escala de GB.** Cada arquivo anual de transações (NCM 4-dígitos) atinge facilmente múltiplos gigabytes. Utilize `polars.scan_csv` (avaliação lazy) ou os converta para `.parquet`; um mero `pd.read_csv` causará Out Of Memory (OOM).
    - **SSL frequentemente quebrado.** O servidor do Siscomex e do MDIC possui a fama de deixar a cadeia de certificados incompleta em curtas janelas de tempo. A CLI possui um fallback não-verificado (unverified context) configurável para não quebrar pipelines noturnos.
    - **Schema NCM vs NBM.** A classificação NCM cobre as transações de 1997 em diante; a NBM cobre o buraco negro de 1989 a 1996 e possui colunas diferentes. Não os concatene de olhos fechados.
    - **A matrix dimensional.** Os arquivos principais trazem apenas IDs numéricos (País=23, UF=1). O real valor analítico só surge quando você faz JOIN com as 20+ tabelas auxiliares (países, municípios, vias de transporte) que a CLI baixa automaticamente.
    - **Idempotência é temporal.** Como não há API moderna fornecendo Hashes, o fetcher usa requisições `HEAD` para validar o cabeçalho `Last-Modified` do servidor FTP/HTTP. Se o MDIC corrigir uma linha do passado, ele baixará novamente o arquivo modificado de forma indetectável para você.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install comex

# Ou como biblioteca no seu projeto
uv add comex-fetcher --index https://index.quantilica.com/simple/
```

**Requisitos:** Python 3.12+

## CLI Oficial (Ambiente Unificado)

A porta de entrada primária para baixar transações internacionais é o executável `quantilica`. A CLI orquestra automaticamente a validação temporal, os retries e o streaming:

```bash
# Baixar exportações e importações completas para 2023 (+ tabelas auxiliares)
quantilica comex sync 2023 -o ./data

# Baixar apenas as importações (de 2018 até 2023), no nível granular de municípios
quantilica comex sync 2018:2023 -imp -mun -o ./data

# Longa duração (multi-GB): clonar a base completa (todos os anos) + tabelas de códigos
quantilica comex sync -o ./data

# Apenas atualizar as tabelas auxiliares
quantilica comex sync --tables-only -o ./data
```

---

## Datasets e Tabelas (Macro-Grupos)

### Transações Comerciais Fato
- `exp` / `imp`: Exportações/Importações normais (1997+, nível UF)
- `exp-mun` / `imp-mun`: Exportações/Importações mais granulares, rastreando o município emissor/receptor.
- `exp-nbm` / `imp-nbm`: Legado histórico (1989-1996) sob a classificação NBM.

### Tabelas Auxiliares (Dimensões)
Ao sincronizar o Comex, a ferramenta puxa silenciosamente dicionários indispensáveis, salvos em `auxiliary-tables/`:
- `ncm` (Nomenclatura Comum do Mercosul), `sh` (Sistema Harmonizado)
- `pais`, `pais-bloco` (Mercosul, União Europeia, etc)
- `uf-mun` (Municípios), `via` (Marítima, Aérea, etc), `urf` (Unidade da Receita Federal)

---

## Cookbook Analítico: Agregações em GBs com Polars

O volume de arquivos CSV gerados pelo SISCOMEX facilmente esgota a memória RAM, especialmente quando você busca granularidade municipal (`-mun`).

Abaixo demonstramos a maneira idiomática de cruzar os dados faturados (gigantescos) com a tabela de códigos NCM (pequena) executando o cálculo inteiramente em *streaming*:

```python
import polars as pl
from pathlib import Path

# 1. Carrega as tabelas pequenas de metadados em memória (Eager)
df_ncm = pl.read_csv(
    "data/secex-comex/auxiliary-tables/ncm.csv",
    separator=";",
    encoding="latin-1"
)

# 2. Registra todos os anos de exportação no motor Lazy
# (O Polars não lê os GBs agora, apenas examina o schema)
df_export = pl.scan_csv(
    "data/secex-comex/exp-mun/*.csv",
    separator=";",
    encoding="latin-1"
)

# 3. Descobrir os 5 produtos que o Brasil mais faturou em Dólar na década
top_commodities = (
    df_export
    # Faz o JOIN com os nomes legíveis antes mesmo de coletar!
    .join(df_ncm.lazy(), left_on="CO_NCM", right_on="CO_NCM", how="left")
    # Agrega o valor total faturado (FOB) em Dólar
    .group_by("NO_NCM_POR")
    .agg(pl.col("VL_FOB").sum().alias("Total_Dolar"))
    .sort("Total_Dolar", descending=True)
    .head(5)
    .collect() # <-- Aqui o motor lê tudo paralelamente otimizando o I/O
)

print(top_commodities)
```

## Resiliência de Rede Oculta
Se a sua conexão cair em 95% do download de um arquivo de 2 GB, o `comex-fetcher` não perde o trabalho. Ele baixa nativamente todos os *chunks* para extensões `.tmp`. Somente após o checksum e sucesso a transferência é efetivada, garantindo escritas 100% atômicas no seu datalake.

## Uso sem Ambiente Unificado (Isolado)

Se necessário num container mínimo:
```bash
comex-fetcher sync 2023 -exp -o /data
comex-fetcher list
```

## Saiba Mais

- **[Macroeconomia IBGE](../ibge/index.md)** — Dados de PIB e economia
- **[Arquitetura do Ecossistema](../concepts/arquitetura.md)** — Design do sistema
