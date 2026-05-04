# Comércio Exterior (Comex)

Dados de importação/exportação brasileira do Siscomex (Sistema Integrado de Comércio Exterior).

**comexdown** é um agente de extração resiliente de rede para dados Siscomex — engenhosamente projetado para lidar com infraestrutura governamental legada com downloads idempotentes e eficiência streaming.

## O Desafio

Extrair dados de comércio brasileiro programaticamente atinge obstáculos reais de infraestrutura:

- **Volume colossal**: Arquivos CSV em escala de gigabytes esgotam downloads ingênuos em memória
- **Servidores instáveis**: Throttling de largura de banda, problemas de certificado SSL, quedas ocasionais
- **Downloads redundantes**: Sem APIs modernas, re-executar pipelines busca novamente arquivos que não mudaram

**comexdown** resolve esses problemas através de downloads idempotentes, chunks streaming, resiliência SSL e auto-retry.

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
pip install comexdown
```

**Requisitos:** Python 3.10+

## CLI

```text
comexdown <command> [args]

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
comexdown trade 2023 -o ./DATA

# Apenas importações, 2018–2023, com breakdown municipal
comexdown trade 2018:2023 -imp -mun -o ./DATA

# Arquivo de história completa única (todos os anos agrupados por SECEX)
comexdown trade complete -o ./DATA

# Tabelas auxiliares
comexdown table all -o ./DATA          # cada tabela
comexdown table ncm pais uf -o ./DATA  # tabelas específicas
comexdown table                        # listar tabelas disponíveis

# Tudo (longa duração, multi-GB)
comexdown all -y -o ./DATA
```

## API Python

Funções de nível superior em `comexdown`:

```python
from pathlib import Path
import comexdown

data_dir = Path("./DATA")

# Transações comerciais para um ano (baseado em NCM, 1997+)
comexdown.get_year(data_dir, year=2023)                     # exports + imports
comexdown.get_year(data_dir, year=2023, exp=True)           # apenas exportações
comexdown.get_year(data_dir, year=2023, imp=True, mun=True) # importações, município

# Dados comerciais antigos baseados em NBM (1989–1996)
comexdown.get_year_nbm(data_dir, year=1995)

# Arquivos históricos completos (um arquivo por direção, todos os anos)
comexdown.get_complete(data_dir)
comexdown.get_complete(data_dir, exp=True, mun=True)

# Tabela de códigos auxiliares
comexdown.get_table(data_dir, table="ncm")
comexdown.get_table(data_dir, table="pais")

# Tudo
comexdown.download_all(data_dir)
```

Helpers de baixo nível em `comexdown.download`: `download_file(url, output, retry=3, blocksize=8192)`, `remote_is_more_recent(headers, dest)`, `get_file_metadata(url)`.

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

Execute `comexdown table` (sem args) para imprimir a lista atual com descrições.

## Layout em Disco

`comexdown` escreve em uma árvore estruturada no caminho de saída:

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
- **[Arquitetura](../architecture/overview.md)** — Design do sistema
