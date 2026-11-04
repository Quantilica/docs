---
title: comex-fetcher — Comércio exterior do Brasil via Siscomex
description: Coleta resiliente do Siscomex (importação e exportação): idempotência temporal, streaming chunked, validação de conteúdo e NCM vigente do Portal Único.
---

# Comércio Exterior (Comex)

Dados de importação e exportação brasileira extraídos do Siscomex (Sistema Integrado de Comércio Exterior).

**comex-fetcher** é um agente de extração resiliente de rede — projetado especificamente para lidar com a infraestrutura governamental legada, superando instabilidades através de downloads idempotentes e eficiência via *chunk streaming*.

!!! warning "Pegadinhas da fonte oficial"

    - **Arquivos em escala de GB.** Cada arquivo anual de transações (NCM 4-dígitos) atinge facilmente múltiplos gigabytes. Utilize `polars.scan_csv` (avaliação lazy) ou os converta para `.parquet`; um mero `pd.read_csv` causará Out Of Memory (OOM).
    - **SSL frequentemente quebrado.** O servidor do Siscomex e do MDIC possui a fama de deixar a cadeia de certificados incompleta em curtas janelas de tempo. A CLI possui um fallback não-verificado (unverified context) configurável para não quebrar pipelines noturnos.
    - **Schema NCM vs NBM.** A classificação NCM cobre as transações de 1997 em diante; a NBM cobre o buraco negro de 1989 a 1996 e possui colunas diferentes. Não os concatene de olhos fechados.
    - **A matrix dimensional.** Os arquivos principais trazem apenas IDs numéricos (País=23, UF=1). O real valor analítico só surge quando você faz JOIN com as 20 tabelas auxiliares (países, municípios, vias de transporte), baixadas no grupo `auxiliary`.
    - **Idempotência é temporal.** Como não há API moderna fornecendo Hashes, o fetcher usa requisições `HEAD` para validar o cabeçalho `Last-Modified` do servidor FTP/HTTP. Se o MDIC corrigir uma linha do passado, ele baixará novamente o arquivo modificado de forma indetectável para você.
    - **`206` no lugar do arquivo.** O host atual (`balanca.mdic.gov.br`) responde `206` com o código-fonte PHP do Joomla quando o arquivo pedido não existe (ano fora da faixa ou ainda não publicado), em vez de `404`. O `sync` valida a primeira linha do CSV/JSON antes de gravar o arquivo e o `convert` confere de novo antes de escrever Parquet: a página de erro vira erro contado, nunca dado.
    - **NCM vigente sem validador de frescor.** O JSON do Portal Único não envia `Last-Modified` nem `ETag`, então o nome carimba a data do download e o `sync` deduplica por `sha256` — sem isso, cada dia nasceria uma "nova versão" do mesmo conteúdo.

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
# Baixar exportações e importações por país e UF (NCM)
quantilica comex sync trade-exp trade-imp -o ./data

# Baixar apenas as importações no nível municipal
quantilica comex sync trade-imp-mun -o ./data

# Longa duração (multi-GB): todos os grupos, sem recorte temporal
quantilica comex sync -o ./data

# Apenas atualizar as tabelas auxiliares
quantilica comex sync auxiliary -o ./data

# NCM vigente do Siscomex e tabelas de correlações de códigos
quantilica comex sync other -o ./data
```

---

## Datasets e Tabelas (Macro-Grupos)

### Transações Comerciais Fato
- `trade-exp` / `trade-imp`: Exportações/Importações normais (1997+, nível UF), em `exp/` e `imp/`.
- `trade-exp-mun` / `trade-imp-mun`: Exportações/Importações mais granulares, rastreando o município emissor/receptor, em `exp-mun/` e `imp-mun/`.
- `trade-exp-nbm` / `trade-imp-nbm`: Legado histórico (1989-1996) sob a classificação NBM.

### Tabelas Auxiliares (Dimensões)
O grupo `auxiliary` (incluído no `sync` sem argumentos, mas não nos grupos `trade-*`) traz 20 dicionários, salvos em `auxiliary-tables/`:
- `ncm` (Nomenclatura Comum do Mercosul), `sh` (Sistema Harmonizado)
- `pais`, `pais_bloco` (Mercosul, União Europeia, etc)
- `uf`, `uf_mun` (UFs e municípios), `via` (Marítima, Aérea, etc), `urf` (Unidade da Receita Federal)
- e outras, como `cuci`, `isic`, `nbm`, `unidade` e `grupo`

Os arquivos levam a data da fonte no nome (por exemplo, `auxiliary-tables/ncm@20240315.csv`).

### Outras tabelas (grupo `other`)

O catálogo tem 10 grupos e 164 entradas. Além dos grupos de transação, do `auxiliary` (20 dicionários) e de `repetro` (2 planilhas de exportação/importação) e `validation` (4 CSVs de totais para conferência), o grupo `other` traz dois itens — entra no `sync` sem argumentos e também pelo alias `tables`:

- **`ncm-vigente`**: a NCM vigente publicada pelo **Portal Único Siscomex** (JSON, ~3 MB), com **15.157 nomenclaturas** — código, descrição, início e fim de vigência e o ato que a instituiu. Não traz TEC, IPI, PIS/Cofins nem alíquotas. Sem `Last-Modified`/`ETag`, o arquivo é carimbado pela data do download em `ncm-vigente/ncm-vigente@AAAAMMDD.json` e deduplicado por `sha256`.
- **`tabelas-auxiliares`**: `TABELAS_AUXILIARES.xlsx`, as tabelas de correlações de códigos e classificações, salvo em `auxiliary-tables/tabelas-auxiliares@AAAAMMDD.xlsx`.

---

## Conversão para o lake

```bash
quantilica comex convert -i ./data --lake /caminho/do/lake
```

- **Transações** (`exp`, `imp`, `exp-mun`, `imp-mun`, `exp-nbm`, `imp-nbm`): Parquet particionado por `ano=<ano>` (inteiro), lido do CSV com separador `;` e `latin-1`. As colunas de código (`co_ncm`, `co_pais`, `co_mun`...) ficam sempre texto, para não perder zero à esquerda.
- **Tabelas de referência** (`auxiliary-tables`, `repetro`, `validacao`, `ncm-vigente`): sem partição.
- **XLSX vira um Parquet por aba**, com chave composta `<arquivo>__<aba>`, sem extensão nem carimbo `@data` na base e com a aba normalizada em `snake_case` (`tabelas-auxiliares@20240315.xlsx` + aba `Tabela 1.1` → `tabelas-auxiliares__tabela_1_1`). Abas vazias ficam de fora; planilha sem nenhuma aba com dados é erro contado. Os nomes de coluna viram `snake_case` e só são convertidos para número quando todo valor converte — nada de virar nulo em silêncio.
- **ZIP vira um Parquet por membro** CSV/XLSX, extraído em streaming para não depender de memória livre. A chave combina arquivo, membro e, quando o membro é um XLSX, a aba dele (`TABELAS_AUXILIARES.zip` + `tabelas.xlsx` + `Tabela 2` → `TABELAS_AUXILIARES__tabelas_xlsx_tabela_2`). Membro de outro tipo ou ZIP sem nenhum membro tabular é **erro contado**, nunca ignorado em silêncio.
- **JSON do Siscomex** (`ncm-vigente`) vira uma tabela longa: `codigo`, `codigo_ncm`, `descricao`, `data_inicio`, `data_fim`, `tipo_ato_ini`, `numero_ato_ini`, `ano_ato_ini`, `nivel_digitos`, `vigente_em` e `ato`.
- De cada base só a **versão vigente** é convertida (`select_current`); versões antigas do mesmo arquivo ficam contadas como puladas. Sidecars `*.manifest.json`, arquivos `*.tmp` e entradas que não se enquadram em CSV/XLSX/ZIP/JSON ficam de fora, e um ano de transação que não se infere do nome é erro contado.

### Reconversão necessária

- Os Parquets de `auxiliary-tables` e `repetro` gerados por versões anteriores guardavam **só a primeira aba** do XLSX: remova-os e reconverta com `--force`.
- Arquivos `.zip` e o JSON do Siscomex não eram convertidos antes (ficavam de fora, sem aviso): converta com `--force` para trazê-los ao lake.

---

## Cookbook Analítico: Agregações em GBs com Polars

O volume de arquivos CSV gerados pelo SISCOMEX facilmente esgota a memória RAM, especialmente quando você busca granularidade municipal (`-mun`).

Abaixo demonstramos a maneira idiomática de cruzar os dados faturados (gigantescos) com a tabela de códigos NCM (pequena) executando o cálculo inteiramente em *streaming*:

```python
import polars as pl
from pathlib import Path

# 1. Carrega as tabelas pequenas de metadados em memória (Eager)
df_ncm = pl.read_csv(
    max(Path("data").glob("auxiliary-tables/ncm@*.csv")),  # nome carimbado com a data da fonte
    separator=";",
    encoding="latin-1"
)

# 2. Registra todos os anos de exportação no motor Lazy
# (O Polars não lê os GBs agora, apenas examina o schema)
df_export = pl.scan_csv(
    "data/exp-mun/*.csv",
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

## Binário `comex-fetcher`

O pacote também instala o comando `comex-fetcher`, equivalente a `quantilica comex`. Ele não dispensa o host: depende do `quantilica-cli` e, sem ele, imprime `Instale via "quantilica install comex"` e sai com código 1.

```bash
comex-fetcher sync trade-exp -o /data
comex-fetcher list
```

## Saiba Mais

- **[Macroeconomia IBGE](../ibge/index.md)** — Dados de PIB e economia
- **[Arquitetura do Ecossistema](../../conceitos/arquitetura.md)** — Design do sistema
