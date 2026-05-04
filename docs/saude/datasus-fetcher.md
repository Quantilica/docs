# Saúde Pública (Saúde)

Dados de vigilância de saúde brasileira do DATASUS (Departamento de Dados de Saúde).

**datasus-fetcher** é um crawler concorrente multithreaded engenhosamente projetado para os microdados massivos do Sistema Único de Saúde (SUS) do Brasil hospedados em servidores FTP legados.

Muito mais que um simples cliente de dados, ele entende a taxonomia complexa dos sistemas de saúde brasileiros (SIHSUS, SIM, SINASC, SIA, etc.) e abstrai a ineficiência da infraestrutura FTP legada em um pipeline de rede de alto desempenho e tolerante a falhas.

## O Desafio

Obter microdados completos de saúde pública brasileira encontra barreiras severas de infraestrutura:

### 1. Limitações do Protocolo FTP

DATASUS hospeda principalmente dados em FTP público (`ftp.datasus.gov.br`). O protocolo FTP é inerentemente:

- Síncrono (um arquivo por vez)
- Propenso a falhas de transferência silenciosas
- Sujeito a timeouts de conexão e throttling de largura de banda
- Largura de banda severamente limitada por thread

### 2. Labirinto de Diretórios & Nomenclatura Críptica

Arquivos (frequentemente em formato proprietário `.dbc`) estão espalhados por dezenas de diretórios aninhados. Nomes de arquivo codificam lógica de negócio complexa posicionalmente:

- `RDSP2001.dbc` = AIH Reduzido, estado SP, Ano 2020, Mês 01
- Parse manual é propenso a erros e frágil

### 3. Downloads Sequenciais Inviáveis

Baixar todos os dados (todos os estados, todos os anos, todos os subsistemas) sequencialmente via scripts pode levar semanas. Falhas de rede no meio da transferência significam perda total de progresso.

**datasus-fetcher** resolve esses problemas através de concorrência multithreaded, parse semântico de arquivo e resumption inteligente.

## Casos de Uso

### Vigilância Epidemiológica

Rastrear surtos de doenças, disseminação geográfica, padrões sazonais e tendências de incidência em tempo real.

### Análise de Mortalidade

Estudar causas de morte, disparidades de saúde por região/demografia e tendências de mortalidade ao longo do tempo usando microdados completos.

### Economia da Saúde & Alocação de Recursos

Analisar padrões de utilização de hospitais, volumes de procedimentos, efetividade de custos e eficiência de alocação de recursos.

### Pesquisa de Desigualdades de Saúde

Examinar disparidades em resultados de saúde, acesso ao cuidado e diferenças de mortalidade entre grupos socioeconômicos e demográficos.

### Estudos de Carga de Doença

Quantificar carga de doença usando datasets completos de SINASC (registros de nascimento) e SIM (mortalidade) para epidemiologia no nível populacional.

## Recursos Principais

- **113 datasets** em todos os principais sistemas de informação de saúde brasileiros
- **320+ GB** de microdados históricos, algumas séries remontam a 1979
- **Downloads multithreaded** — conexões paralelas configuráveis para recuperação mais rápida
- **Filtragem inteligente** — fatia por intervalo de data e/ou estado (UF) antes de baixar
- **Verificações de integridade de arquivo** — pula arquivos já baixados comparando tamanhos
- **Retries automáticos** — até 3 tentativas em erros FTP transitórios
- **Versionamento de arquivo** — armazena cada versão baixada com nome com data; arquiva antigas automaticamente
- **Documentação & tabelas auxiliares** — baixa livros de códigos e tabelas de referência junto aos dados
- **Sem dependências externas** — Python 3.10+ puro

## Instalação

```bash
pip install datasus-fetcher
```

Para instalação global isolada (recomendado para uso CLI apenas):

```bash
pipx install datasus-fetcher
```

## Início Rápido

Baixar SIH-RD (Admissões Hospitalares) para São Paulo, Rio de Janeiro e Minas Gerais de 2020 a 2023:

```bash
datasus-fetcher data --data-dir /caminho/para/dados sih-rd \
    --start 2020-01 \
    --end 2023-12 \
    --regions sp rj mg
```

Baixar todos os datasets (aviso: 320+ GB total):

```bash
datasus-fetcher data --data-dir /caminho/para/dados
```

## Referência de Comando

datasus-fetcher expõe cinco subcomandos:

### `data` — Baixar arquivos de microdados

```bash
datasus-fetcher data --data-dir <DIR> [DATASETS...] [OPTIONS]
```

| Argumento | Descrição |
|---|---|
| `DATASETS` | Um ou mais códigos de dataset (ex. `sih-rd cnes-st`). Omita para baixar todos os datasets. |
| `--data-dir DIR` | **Obrigatório.** Diretório local onde os arquivos serão armazenados. |
| `--start PERIOD` | Início do filtro de data. Formato: `YYYY` ou `YYYY-MM`. |
| `--end PERIOD` | Fim do filtro de data. Formato: `YYYY` ou `YYYY-MM`. |
| `--regions UF ...` | Um ou mais códigos de estado em minúscula (ex. `sp rj mg ba`). |
| `-t, --threads N` | Número de threads de download concorrentes (padrão: `2`). |
| `--dry-run` | Lista os arquivos que seriam baixados (com tamanhos e totais) sem baixá-los. |

**Exemplos:**

```bash
# Notificações de dengue de SINAN — todos os anos, todos os estados
datasus-fetcher data --data-dir ./data sinan-deng

# Estabelecimentos CNES para todo o Nordeste, a partir de 2015
datasus-fetcher data --data-dir ./data cnes-st \
    --start 2015-01 \
    --regions al ba ce ma pb pe pi rn se

# Registros de morte SIM (ICD-10) de 2000 a 2023
datasus-fetcher data --data-dir ./data sim-do-cid10 \
    --start 2000 --end 2023

# Acelere downloads com mais threads paralelas
datasus-fetcher data --data-dir ./data sih-rd --threads 4
```

### `list-datasets` — Inspecionar datasets disponíveis

Conecta ao servidor FTP do DATASUS e imprime contagens de arquivo, tamanhos e intervalos de data para cada dataset:

```bash
datasus-fetcher list-datasets

# Inspecionar apenas datasets específicos
datasus-fetcher list-datasets sih-rd sia-pa cnes-pf
```

### `docs` — Baixar arquivos de documentação

Baixa arquivos de documentação oficial (dicionários de dados, livros de códigos) para cada sistema:

```bash
# Baixar docs para sistemas específicos
datasus-fetcher docs --data-dir ./docs sih cnes sia sim sinan

# Baixar docs para todos os sistemas
datasus-fetcher docs --data-dir ./docs
```

### `aux` — Baixar tabelas de referência auxiliares

Baixa tabelas de lookup/referência (códigos ICD, códigos de município, tabelas de procedimentos, códigos de ocupação, etc.):

```bash
# Baixar tabelas auxiliares para sistemas específicos
datasus-fetcher aux --data-dir ./aux sih cnes

# Baixar tabelas auxiliares para todos os sistemas
datasus-fetcher aux --data-dir ./aux
```

### `archive` — Mover versões antigas de arquivo para um arquivo

DATASUS periodicamente atualiza seus arquivos. datasus-fetcher armazena cada versão baixada com nome com data. Use `archive` para mover versões não-latest para um diretório separado:

```bash
datasus-fetcher archive \
    --data-dir ./data \
    --archive-data-dir ./data-archive
```

## Estrutura de Armazenamento

Arquivos baixados são organizados em uma árvore de diretórios estruturada:

```
data/
└── sih-rd/
    ├── 199201/                              ← diretório partição YYYYMM
    │   └── sih-rd_sp_199201_20250218.dbc   ← dataset_uf_período_datadedownload.dbc
    ├── 202001/
    │   ├── sih-rd_sp_202001_20250218.dbc
    │   └── sih-rd_rj_202001_20250218.dbc
    └── 202312/
        └── sih-rd_mg_202312_20250218.dbc
```

Para datasets com apenas ano (ex. SIM, SINASC):

```
data/
└── sim-do-cid10/
    └── 2023/
        ├── sim-do-cid10_sp_2023_20250218.dbc
        └── sim-do-cid10_rj_2023_20250218.dbc
```

Cada nome de arquivo codifica: **dataset** + **estado (UF)** + **período** + **data de download**.

## Configuração de Logging

datasus-fetcher registra o progresso de download no console por padrão. Você pode substituir isso colocando um arquivo `logging.ini` no seu diretório de trabalho.

## Datasets Disponíveis

datasus-fetcher suporta **113 datasets** em todos esses sistemas:

- **SIHSUS** — Admissões hospitalares
- **SIM** — Registros de mortalidade (ICD-9 e ICD-10)
- **SINASC** — Registros de nascimento
- **SIA** — Procedimentos ambulatoriais e produção ambulatória
- **CNES** — Registro de instalações de saúde (estabelecimentos, profissionais, equipamentos, serviços)
- **SINAN** — Doenças notificáveis (dengue, tuberculose, HIV e 60+ outras)
- **E mais** — SISCOLO, SISMAMA, SISPRENATAL, bases populacionais, dados territoriais

Para uma lista completa com contagens de arquivo e intervalos de datas, use:

```bash
datasus-fetcher list-datasets
```

## Códigos de Estados Brasileiros

Use códigos de duas letras em minúscula com `--regions`. Códigos comuns:

| Código | Estado | Código | Estado |
|--------|--------|--------|--------|
| `sp` | São Paulo | `ba` | Bahia |
| `rj` | Rio de Janeiro | `mg` | Minas Gerais |
| `rs` | Rio Grande do Sul | `sc` | Santa Catarina |
| `ce` | Ceará | `pe` | Pernambuco |

Veja a lista completa no [README](https://github.com/Quantilica/datasus-fetcher).

## Lendo Arquivos DBC

datasus-fetcher baixa arquivos `.dbc`, que são um formato comprimido usado pelo DATASUS. Para ler esses arquivos em Python, você pode usar pacotes como:

- [PySUS](https://github.com/AlertaDengue/PySUS)
- [read.dbc](https://github.com/Quantilica/read.dbc) (R)
- [dbf2dbc](https://github.com/AlertaDengue/dbf2dbc) (ferramenta de conversão)

## Saiba Mais

- **[Pesquisas de Saúde IBGE](../ibge/index.md)** — Estatísticas de saúde populacional
- **[Arquitetura da Plataforma](../concepts/arquitetura.md)** — Design do sistema
- **[DATASUS Oficial (Português)](https://datasus.saude.gov.br/)** — Fonte governamental
