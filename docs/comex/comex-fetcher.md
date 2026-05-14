---
title: comex-fetcher — Comércio exterior do Brasil via Siscomex
description: Downloader resiliente para os arquivos GB do Siscomex (importação e exportação). Idempotência temporal, streaming chunked, tolerância a SSL ruim.
---

# Comércio Exterior (Comex)

Dados de importação/exportação brasileira do Siscomex (Sistema Integrado de Comércio Exterior).

**comex-fetcher** é um agente de extração resiliente de rede para dados Siscomex — projetado para lidar com a infraestrutura governamental legada com downloads idempotentes e eficiência streaming.

!!! warning "Pegadinhas da fonte oficial"

    - **Arquivos em escala de GB.** Cada arquivo anual de NCM 4-dígitos passa fácil de 1 GB. Use sempre o reader em chunks; `pd.read_csv` cru estoura memória.
    - **SSL frequentemente quebrado.** O servidor do Siscomex tem cadeia de certificados incompleta em janelas curtas. O `comex-fetcher` tem fallback configurável.
    - **Schema NCM vs NBM.** NCM cobre 1997+; NBM cobre 1989–1996 com colunas diferentes. Não confunda o dataset histórico com o atual.
    - **Códigos auxiliares são tabelas separadas.** País, UF, via de transporte, URF — 20+ tabelas de código. Sem juntar essas dimensões, "valor" sozinho não diz nada.
    - **Idempotência é temporal, não por hash.** Arquivos do mesmo período não são re-baixados; mas se o Siscomex republicar com correção, você precisa forçar re-download.
    - **Mês corrente é parcial.** O Siscomex publica o mês fechado por volta do dia 15 do mês seguinte. Não tire conclusões de séries com o último ponto incompleto.

## O Desafio

Extrair dados de comércio brasileiro programaticamente atinge obstáculos reais de infraestrutura:

- **Volume colossal**: Arquivos CSV em escala de gigabytes esgotam downloads ingênuos em memória
- **Servidores instáveis**: Throttling de largura de banda, problemas de certificado SSL, quedas ocasionais
- **Downloads redundantes**: Sem APIs modernas, re-executar pipelines busca novamente arquivos que não mudaram

**comex-fetcher** resolve esses problemas através de downloads idempotentes, chunks streaming, resiliência SSL e auto-retry.

## Casos de Uso

### Análise de Comércio

Entender os padrões de exportação, especialização e vantagem comparativa do Brasil por commodity e destino.

### Estudos de Competitividade

Analisar crescimento de exportações, diversificação de produtos, penetração de mercado e posição competitiva.

### Indicadores Econômicos

Saldo comercial e fluxos como indicadores antecedentes de atividade econômica e movimentos cambiais.

### Pesquisa de Cadeia de Suprimentos

Rastrear importações de bens intermediários, insumos e equipamentos de capital por setor.

### Inteligência de Mercado

Monitorar países concorrentes e tendências de acesso ao mercado.

## Recursos

- **Idempotência temporal** — requisição HEAD verifica `Last-Modified`; pula arquivos já atualizados
- **Downloads streaming** — chunks de 8 KiB; memória constante independente do tamanho do arquivo
- **Escritas atômicas** — downloads para `*.tmp` e renomeia no sucesso; arquivos parciais nunca aparecem
- **Auto-retry** — até 3 tentativas com backoff exponencial (1 s → 2 s → 4 s)
- **Resiliência SSL** — usa contexto SSL não verificado para servidores SECEX com certificados expirados/mal configurados
- **Sem dependências terceirizadas** — biblioteca padrão pura (`urllib`, `ssl`, `http.client`)

## Instalação

```bash
pip install git+https://github.com/Quantilica/comex-fetcher.git
```

**Requisitos:** Python 3.10+

## CLI

```text
comex-fetcher <command> [args]

Comandos:
  trade YEARS [-exp] [-imp] [-mun] [-o PATH]
        Baixar transações comerciais para um ano, um intervalo (2018:2023), ou 'completo'.
        -exp / -imp restringem a direção; padrão baixa ambas.
        -mun adiciona arquivos no nível municipal (1997+).
  table [TABLES...] [-o PATH]
        Baixar tabelas de códigos auxiliares. 'all' baixa cada tabela.
        Execute sem argumentos para imprimir a lista de tabelas disponíveis.
  all   [-y] [-o PATH]
        Baixar TUDO (todos os anos, todas as tabelas, todos os datasets). Pede
        confirmação a menos que -y seja fornecido.
```

`PATH` padrão é `data/secex-comex`.

### Exemplos

```bash
# Exportações + importações para 2023
comex-fetcher trade 2023 -o ./DATA

# Apenas importações, 2018–2023, com breakdown municipal
comex-fetcher trade 2018:2023 -imp -mun -o ./DATA

# Arquivo de história completa única (todos os anos agrupados por SECEX)
comex-fetcher trade complete -o ./DATA

# Tabelas auxiliares
comex-fetcher table all -o ./DATA          # cada tabela
comex-fetcher table ncm pais uf -o ./DATA  # tabelas específicas
comex-fetcher table                        # listar tabelas disponíveis

# Tudo (longa duração, multi-GB)
comex-fetcher all -y -o ./DATA
```

## API Python

Funções de nível superior em `comex-fetcher`:

```python
from pathlib import Path
import comex_fetcher

data_dir = Path("./DATA")

# Transações comerciais para um ano (baseado em NCM, 1997+)
comex_fetcher.get_year(data_dir, year=2023)                     # exports + imports
comex_fetcher.get_year(data_dir, year=2023, exp=True)           # apenas exportações
comex_fetcher.get_year(data_dir, year=2023, imp=True, mun=True) # importações, município

# Dados comerciais antigos baseados em NBM (1989–1996)
comex_fetcher.get_year_nbm(data_dir, year=1995)

# Arquivos históricos completos (um arquivo por direção, todos os anos)
comex_fetcher.get_complete(data_dir)
comex_fetcher.get_complete(data_dir, exp=True, mun=True)

# Tabela de códigos auxiliares
comex_fetcher.get_table(data_dir, table="ncm")
comex_fetcher.get_table(data_dir, table="pais")

# Tudo
comex_fetcher.download_all(data_dir)
```

Helpers de baixo nível em `comex_fetcher.download`: `download_file(url, output, retry=3, blocksize=8192)`, `remote_is_more_recent(headers, dest)`, `get_file_metadata(url)`.

## Datasets

### Transações comerciais

| Dataset | Cobertura | Notas |
|---|---|---|
| `exp`, `imp` | 1997–presente | Baseado em NCM, granularidade mensal |
| `exp-mun`, `imp-mun` | 1997–presente | Mesmo, com município de origem/destino |
| `exp-nbm`, `imp-nbm` | 1989–1996 | Pré-NCM, classificação NBM |
| `exp-completa`, `imp-completa` | histórico completo | Arquivo único agrupado por direção |
| `exp-mun-completa`, `imp-mun-completa` | histórico completo | Mesmo, com município |

### Totais de validação (somas cross-check)

`exp-validacao`, `imp-validacao`, `exp-mun-validacao`, `imp-mun-validacao`.

### REPETRO (regime especial de petróleo & gás)

`exp-repetro`, `imp-repetro`.

### Tabelas auxiliares

`ncm`, `sh`, `cuci`, `cgce`, `isic`, `siit`, `fat-agreg`, `unidade`, `ppi`, `ppe`, `grupo`, `pais`, `pais-bloco`, `uf`, `uf-mun`, `via`, `urf`, `isic-cuci`, `nbm`, `ncm-nbm`.

Execute `comex-fetcher table` (sem args) para imprimir a lista atual com descrições.

## Layout em Disco

`comex-fetcher` escreve em uma árvore estruturada no caminho de saída:

```
data/secex-comex/
├── exp/2023.csv
├── imp/2023.csv
├── exp-mun/2023.csv
├── exp-nbm/1995.csv
├── exp-completa.csv
├── auxiliary-tables/<table>.csv
├── validacao/<file>
└── repetro/<file>
```

## Idempotência

Todo download começa com um HEAD request. `remote_is_more_recent` compara `Last-Modified` contra o `mtime` do arquivo local; se o arquivo local está atualizado o GET é pulado inteiramente. Após um download bem-sucedido o `mtime` do arquivo é configurado de `Last-Modified`, então a próxima execução o encontra idempotente sem re-buscar.

## Fonte de Dados

[Ministério do Desenvolvimento, Indústria, Comércio e Serviços — Estatísticas de Comércio Exterior](https://www.gov.br/produtividade-e-comercio-exterior/pt-br/assuntos/comercio-exterior/estatisticas/base-de-dados-bruta).

## Saiba Mais

- **[Macroeconomia IBGE](../ibge/index.md)** — Dados de PIB e economia
- **[Arquitetura do Ecossistema](../concepts/arquitetura.md)** — Design do sistema
