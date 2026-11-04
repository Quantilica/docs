---
title: b3-fetcher — COTAHIST, derivativos agro e carteiras de índices da B3
description: Baixa o COTAHIST da B3 desde 1986, as posições em aberto de derivativos agropecuários e a composição dos índices, com leitura em Polars e Decimal exato.
---

# `b3-fetcher`

O `b3-fetcher` baixa três famílias de dados da B3 (Brasil, Bolsa, Balcão): a série histórica de cotações **COTAHIST**, as posições em aberto de **derivativos agropecuários** e a composição vigente das **carteiras de índices**. Os registros de cotação são lidos em um DataFrame do Polars.

| | |
|---|---|
| **Fonte** | B3: série histórica de cotações (`bvmf.bmfbovespa.com.br/InstDados/SerHist`), API de arquivos (`arquivos.b3.com.br/api`) e composição de índices (`sistemaswebb3-listados.b3.com.br`) |
| **Cobertura** | COTAHIST de 1986 até o ano corrente, sem ajuste de proventos; derivativos e carteiras, em janela curta de dias úteis |
| **Formato** | um ZIP por ano (`COTAHIST_A<ano>.zip`) com um TXT de largura fixa; CSV diário de derivativos; JSON de carteira |
| **Grupo** | `cotacaohistorica` (por ano), `derivativos_agro` (por dia útil) e `indices_carteiras` (por índice) |
| **Escopo do pacote** | download, leitura, conversão para o lake e manifest. A carga em banco não faz parte do fetcher |

!!! warning "Pegadinhas da fonte"

    - **Largura fixa, não CSV.** Cada linha tem exatamente 245 bytes em `latin-1`. O primeiro par de caracteres é o tipo do registro: `00` (cabeçalho), `01` (cotação) e `99` (rodapé).
    - **Vírgula implícita.** Preços e volumes não trazem separador decimal. `(11)V99` em 13 posições significa 2 casas decimais. O `reader` aplica isso lendo o layout, e entrega `Decimal` exato, nunca `float`.
    - **Preços sem ajuste.** Desdobramentos, grupamentos e proventos não são aplicados. Uma série longa de um papel tem saltos que não são movimento de mercado.
    - **Extensão do membro do ZIP muda.** Os arquivos recentes trazem um `.TXT`; os antigos, um único membro sem extensão. O `reader` trata os dois.
    - **Arquivos diários não têm URL estável.** `derivativos_agro` é pedido por `requestname?fileName=...&date=...`, que devolve um token para o download; o `400` significa "sem arquivo" (fim de semana, feriado, data futura ou nome desconhecido) e é ignorado sem erro. `indices_carteiras` é lido do `GetPortfolioDay`, que só serve a carteira vigente — a data do arquivo vem do cabeçalho da resposta, não do pedido.
    - **IBRx 100 se chama `IBXX` na API.** Pedir `IBRX100` devolve `200` com corpo vazio; o pacote traduz a sigla do Lake para o código aceito pela B3.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install b3

# Ou como biblioteca no seu projeto
uv add b3-fetcher --index https://index.quantilica.com/simple/
```

A leitura dos registros (`b3_fetcher.reader`) exige o extra `analysis`, que traz o Polars:

```bash
quantilica install b3 --extra analysis
# ou, no seu projeto:
uv add 'b3-fetcher[analysis]' --index https://index.quantilica.com/simple/
```

**Requisitos:** Python 3.12+

## Primeiro dado

```bash
quantilica b3 sync cotacaohistorica -o ./data/b3
```

Isso baixa todos os anos disponíveis, um arquivo por ano, com um manifest SHA-256 ao lado de cada ZIP. Para ver o que seria baixado, sem baixar:

```bash
quantilica b3 sync --dry-run -o ./data/b3
```

Os outros dois grupos pedem protocolo próprio e entram do mesmo jeito:

```bash
# Posições em aberto de derivativos agropecuários (últimos dias úteis)
quantilica b3 sync derivativos_agro -o ./data/b3

# Carteira vigente dos índices IBOV, IBRX100, SMLL, IDIV, IFIX e IFIL
quantilica b3 sync indices_carteiras -o ./data/b3
```

!!! note "Volume"

    O ZIP de 1986 tem cerca de 8 MB e traz 177.981 registros de cotação. Os anos recentes são bem maiores. Para um primeiro teste, use `--dry-run`.

## Comandos

| Comando | O que faz |
|---|---|
| `quantilica b3 list` | Lista todas as partições do catálogo, uma tabela por grupo: anos de 1986 ao ano corrente (`cotacaohistorica`), dias úteis da janela (`derivativos_agro`) e um registro por índice (`indices_carteiras`), cada um com sua URL |
| `quantilica b3 check` | Compara o disco com o remoto e diz o que está desatualizado, sem baixar. `--json` imprime o plano e `--out` o grava. Datas sem arquivo aparecem como `skip-unavailable`, não como erro |
| `quantilica b3 sync` | Baixa os grupos pedidos (padrão: todos). `--output`/`-o` define o diretório, `--workers` os downloads paralelos (padrão 4), `--dry-run` só lista e `--force` ignora a checagem de frescor |
| `quantilica b3 convert` | Converte o acervo bruto para o lake Hive em Parquet. `-i/--input` é a origem (padrão `/data/b3`), `--lake` a raiz do lake (padrão `QUANTILICA_LAKE_DIR`), `--dataset` filtra datasets e `--force` reconverte mesmo com o `sha256` coincidindo |
| `quantilica b3 pipeline` | Baixa e converte em uma só execução (`sync` + `convert`), com os mesmos grupos e flags dos dois comandos |

O fluxo recomendado é `check --out plano.json` seguido de `sync --from-plan plano.json`: baixa só o que mudou.

A janela de `derivativos_agro` é de 5 dias úteis (hoje inclusive), configurável com `B3_LOOKBACK_DAYS`. Feriados não são conhecidos pelo pacote: a B3 responde `400` e a data é pulada.

### Onde os arquivos ficam

```text
data/b3/
├── cotacaohistorica/
│   └── 2025/
│       ├── cotacaohistorica_2025@<data>.zip
│       └── cotacaohistorica_2025@<data>.zip.manifest.json
├── derivativos_agro/
│   └── 2026/
│       └── derivativos_agro-2026-11-03.csv
└── indices_carteiras/
    └── 2026/
        └── indices_carteiras-IBOV-2026-11-03.json
```

A data no nome do COTAHIST vem do `Last-Modified` do servidor. Uma nova versão remota do mesmo ano vira um arquivo novo, sem sobrescrever o anterior. Nos grupos diários a data é a do dado (dia útil pedido ou data da carteira), e o arquivo é final: não há `Last-Modified` nem `HEAD` nesses endpoints.

## Lendo os registros

```python
from pathlib import Path

from b3_fetcher.reader import read_dimension, read_records

df = read_records(Path("data/b3/cotacaohistorica/1986/cotacaohistorica_1986@<data>.zip"))
print(df.schema)
```

`read_records` aceita o `.zip` baixado ou o `.txt` já extraído e devolve só os registros `01`. As conversões são estritas: um campo em branco vira nulo, mas um valor que não cabe no tipo do layout levanta erro em vez de virar nulo em silêncio.

Colunas principais:

| Coluna | Tipo | Significado |
|---|---|---|
| `data` | `Date` | Data do pregão |
| `simbolo` | `String` | Código de negociação do papel |
| `nome_resumido` | `String` | Nome resumido da empresa emissora |
| `tipo_mercado_id` | `Int64` | Tipo de mercado (ver `read_dimension("tpmerc")`) |
| `bdi_id` | `String` | Código BDI (ver `read_dimension("codbdi")`) |
| `especificacao_id` | `String` | Especificação do papel (ver `read_dimension("especi")`) |
| `preco_abertura`, `preco_maximo`, `preco_minimo`, `preco_medio`, `preco_ultimo_negocio` | `Decimal(13, 2)` | Preços do pregão |
| `quantidade_negocios`, `quantidade_titulos_negociados` | `Int64` | Número de negócios e de títulos negociados |
| `volume_negociado` | `Decimal(18, 2)` | Volume financeiro |
| `data_vencimento` | `Date` | Vencimento (opções e termo) |
| `fator_cotacao` | `Int64` | Fator de cotação do papel |

As 26 colunas completas seguem o layout oficial do registro `01`.

### Tabelas auxiliares

```python
read_dimension("tpmerc")   # tipo de mercado
read_dimension("codbdi")   # código BDI
read_dimension("especi")   # especificação do papel
read_dimension("indopc")   # índice de correção de opções
```

Cada tabela vem com nomes de coluna canônicos (`tipo_mercado_id`/`tipo_mercado`, `bdi_id`/`bdi` e assim por diante), prontos para `join` com `read_records`.

### Salvando em Parquet

```python
from b3_fetcher.reader import write_parquet

write_parquet(df, Path("data/b3/parquet/1986.parquet"), source_path=zip_path)
```

Com `source_path`, o manifest do ZIP original é copiado para os metadados do Parquet, preservando a proveniência. A escrita é atômica e usa compressão zstd.

## Derivativos agropecuários (`derivativos_agro`)

Posições em aberto de derivativos do segmento `AGRIBUSINESS`, um arquivo por dia útil da janela (`DerivativesOpenPosition`, CSV com `;` e UTF-8).

- **Pedido em duas etapas.** `GET requestname?fileName=DerivativesOpenPosition&date=AAAA-MM-DD` devolve JSON com o token; o download é `GET download/?token=...`. O `400` do `requestname` vira "sem arquivo" e a data é pulada sem erro (fim de semana, feriado, data futura).
- **Só o segmento agro.** O arquivo traz todos os segmentos; o conversor filtra `AGRIBUSINESS` e grava **um Parquet por ativo-objeto** (`BGI`, `CCM`, `ICF`, `SJC`, `ETH`, `CNL`...).
- **Leitura estrita.** Tudo entra como texto primeiro (ticker e ISIN nunca viram número); só as colunas de quantidade são convertidas, com erro em vez de nulo silencioso. `preco_termo` chega como vírgula decimal e vira `Decimal`. As colunas são renomeadas para português: `data_referencia`, `ticker`, `codigo_isin`, `ativo_objeto`, `contratos_em_aberto`, `variacao_contratos_em_aberto`, `total_posicoes` e assim por diante.
- **Cabeçalho pode vir com uma linha antes.** Quando o arquivo começa com `Status do Arquivo: Final`, essa linha é pulada; cabeçalho inesperado é erro contado.

## Carteiras de índices (`indices_carteiras`)

Composição e pesos teóricos vigentes de **IBOV, IBRX100, SMLL, IDIV, IFIX e IFIL**, lidos do `GetPortfolioDay` (parâmetro JSON compacto em base64).

- **Só a carteira vigente.** O endpoint ignora a data pedida e devolve a composição atual; o nome do arquivo usa a data do cabeçalho da resposta. Sem `header`/`results` a resposta é erro (`GetPortfolioDay` responde `200` com corpo vazio para índice inexistente).
- **IBRx 100 é `IBXX`.** A sigla do Lake é `IBRX100`; o código aceito pela B3 é `IBXX`. Os demais usam o mesmo nome nos dois lados.
- **Colunas.** `segmento`, `ticker`, `nome`, `especie`, `participacao_pct` e `participacao_acumulada_pct` (`Decimal(12, 6)`), `qtd_teorica` (inteiro), `data_carteira`, `redutor` e `qtd_teorica_total`.

## Particionamento no lake

| Dataset | Partição | Origem |
|---|---|---|
| `cotacaohistorica` | `ano` | ZIP anual, registros `01` do COTAHIST |
| `derivativos_agro` | `ano`, `mes`, `dia`, `contrato` | CSV diário, só `AGRIBUSINESS`, um Parquet por ativo-objeto |
| `indices_carteiras` | `indice`, `ano`, `mes`, `dia` | JSON da carteira vigente, pesos em decimal |

Aliases de conversão: `cotahist`, `derivativos-agro` e `indices-carteiras`. Um arquivo cujo dataset, data ou índice não se infere do nome é **erro contado** do `convert` — nada cai em `cotacaohistorica`, em `01/01` ou na data de hoje por omissão. Sidecars `*.manifest.json` são ignorados.

## Particularidades

- **Primeiro ano:** `COTAHIST_A1985.zip` responde `404`. A série começa em 1986.
- **Outras granularidades:** a B3 também publica arquivos mensais e diários. O pacote expõe `build_monthly_url` e `build_daily_url` para montar essas URLs, mas o `sync` trabalha com os arquivos anuais.
- **BTC (empréstimo de ativos) não é coletado:** o grupo `btc_posicoes_abertas` saiu do catálogo. A API `requestname` responde `400` para qualquer nome de arquivo testado e não há tabela publicada para esse dado; o que se publica parece estar identificado pelo código BDI dos próprios registros do COTAHIST (`read_dimension("codbdi")`). Não há stub: o grupo não aparece em `list` nem em `sync`.
- **Frescor:** os arquivos do COTAHIST usam `Last-Modified` com fallback para `GET` quando o servidor não responde `HEAD` corretamente. Os endpoints diários não têm `HEAD` nem `ETag` — por isso o caminho é token e carteira, com o nome do arquivo já final.
- **Validação:** na primeira publicação, os 40 arquivos anuais de 1986 a 2025 foram lidos sem erro nem nulo inesperado.

## Saiba mais

- [Changelog do pacote](https://github.com/Quantilica/b3-fetcher/blob/main/CHANGELOG.md)
- [Repositório](https://github.com/Quantilica/b3-fetcher)
- [Convenções de armazenamento](../../conceitos/storage.md) e [proveniência e manifestos](../../conceitos/proveniencia.md)
