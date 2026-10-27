---
title: Padronização de Lake Hive (Parquet)
description: "Norma técnica do layout particionado Hive, metadados, descritor _dataset.json, garantias de atomicidade e integração com quantilica-cli e quantilica-analytics."
---

# Padronização de Lake Hive (Parquet)

Esta norma técnica estabelece o padrão canônico para o lago de dados particionado em formato Parquet no ecossistema Quantilica. Define a convenção de diretórios baseada no padrão Hive, a estrutura do descritor de conjunto de dados (`_dataset.json`), os metadados de rodapé obrigatórios, as garantias de atomicidade e concorrência na escrita via `LakeWriter`, a interoperabilidade entre motores analíticos (DuckDB, Polars e PyArrow) e a integração com coletores (`fetchers`) e com a interface de linha de comando (`quantilica-cli`).

---

## 1. Visão Geral e Princípios Fundamentais

O ecossistema adota uma arquitetura em três camadas fundamentais para o processamento de dados públicos:

1. **Camada Bruta (`raw`)**: Armazena os artefatos originais obtidos diretamente dos portais governamentais (arquivos compactados em formatos como `.zip` ou `.7z`, tabelas em `.csv`, `.txt`, `.dbf`, entre outros). Cada arquivo baixado é acompanhado de um manifesto de proveniência (`.manifest.json`) contendo a URL de origem, o carimbo de data/hora do download e o hash SHA-256 de validação.
2. **Camada de Lake (`lake`)**: Armazena os dados descompactados, normalizados e convertidos para arquivos colunares Parquet particionados segundo o layout Hive. É projetada para análise massiva em disco local ou armazenamento compartilhado.
3. **Camada de Serviço / Marts (`marts` e PostgreSQL)**: Armazena exclusivamente séries consolidadas, agregações analíticas e tabelas de consulta direta necessárias para aplicações e interfaces web.

### Princípio da separação de carga

O banco de dados relacional (PostgreSQL) guarda apenas o que é servido para consultas operacionais e agregações curadas. Bases volumosas de microdados (como RAIS, CAGED, DATASUS, CVM, INEP e CNPJ da Receita Federal) não devem ser carregadas integralmente no PostgreSQL. Essas bases residem no Lake Hive em Parquet, preservando a eficiência computacional e a capacidade transacional do banco de dados.

### Desacoplamento arquitetural

O Lake Hive é uma camada conceitual do ecossistema, não um pacote de software isolado. Qualquer ferramenta ou coletor que respeite o layout e o contrato de metadados pode gravar no lago; qualquer motor analítico ou aplicação que suporte o padrão Parquet/Hive pode ler o lago sem precisar conhecer o coletor que originou o arquivo.

---

## 2. Convenção de Diretórios e Nomenclatura

### Raiz do Lake

A raiz do lago é resolvida pela função `lake_root()` de `quantilica.core.lake`, respeitando a seguinte ordem de precedência:

1. Variável de ambiente `QUANTILICA_LAKE_DIR`;
2. Subdiretório `lake` apontado por `QUANTILICA_DATA_DIR` (`$QUANTILICA_DATA_DIR/lake`);
3. Caminho padrão no diretório do usuário: `~/data/lake`.

### Estrutura de diretórios

Dentro da raiz, a hierarquia organiza-se por fonte de dados (`source_id`), conjunto de dados (`dataset_id`) e níveis sucessivos de partição no formato Hive (`chave=valor`):

```
$QUANTILICA_LAKE_DIR/
└── <source_id>/
    └── <dataset_id>/
        ├── _dataset.json
        ├── .lock
        ├── .tmp/
        └── <k1>=<v1>/
            └── [<k2>=<v2>/...]
                └── <file_key>[-NNN].parquet
```

Cada conjunto de dados possui, em sua raiz:

- `_dataset.json`: Arquivo obrigatório de metadados que descreve o schema, as chaves de partição e os tipos associados.
- `.lock`: Arquivo de lock cooperativo utilizado durante operações de escrita concorrente.
- `.tmp/`: Diretório temporário de trabalho no mesmo sistema de arquivos, viabilizando movimentações atômicas de publicação.

### Regras de nomenclatura e sanitização

- **Chaves de partição (`key`)**: Devem seguir estritamente o formato snake_case ASCII minúsculo correspondente à expressão regular `^[a-z][a-z0-9_]*$`. Exemplo: `ano`, `mes`, `regiao`, `uf`.
- **Valores de partição (`value`)**: Devem conter apenas caracteres alfanuméricos ASCII, ponto, sublinhado ou hífen, correspondentes à expressão regular `^[0-9A-Za-z._-]+$`. Os valores `.` e `..` são expressamente proibidos por violarem o confinamento de diretórios.
- **Partições nulas ou faltantes**: Quando um arquivo ou registro não possui valor para uma determinada chave de partição, o valor do diretório deve ser obrigatoriamente a constante canônica do Hive:
  ```
  __HIVE_DEFAULT_PARTITION__
  ```
- **Identificador de arquivo (`file_key`)**: O nome base do arquivo Parquet corresponde ao `file_key` extraído pela função `file_key()` de `quantilica.core.lake`. Essa função remove extensões compostas brutas (como `.csv`, `.tsv`, `.7z`, `.zip`, `.tar.gz`) e sufixos de carimbo de download iniciados por `@` (como `@20261021`). Exemplo: o arquivo `caged_202401@20260513.7z` gera o arquivo `caged_202401.parquet`.
- **Particionamento em partes (`-NNN`)**: Quando um arquivo gerador é subdividido em blocos menores (para atender a um limite máximo de tamanho em bytes), os arquivos recebem um sufixo numérico de três dígitos a partir de `001`: `<file_key>-001.parquet`, `<file_key>-002.parquet`, etc. Se não houver divisão, o arquivo é gravado sem sufixo numérico: `<file_key>.parquet`.

### Regra fundamental de não redundância

> **Regra de ouro:** As colunas que compõem o caminho de partição Hive **NÃO** podem ser armazenadas como colunas de dados dentro do arquivo Parquet físico.

Motores analíticos compatíveis com particionamento Hive (DuckDB, Polars e PyArrow) extraem as colunas de partição dinamicamente a partir dos nomes dos diretórios no momento da leitura. Duplicar essas colunas no payload interno dos arquivos Parquet desperdiça espaço em disco, sobrecarrega a descompressão e gera inconsistências de schema. O checker de conformidade recusa datasets que apresentem colunas de partição no interior dos arquivos físicos.

---

## 3. Metadados Obrigatórios do Parquet

Cada arquivo Parquet persistido no lake deve conter um conjunto padronizado de chaves de metadados no rodapé do arquivo (*footer KV metadata*), sob o prefixo `quantilica.*`.

| Chave | Descrição | Exemplo |
|---|---|---|
| `quantilica.lake.layout_version` | Versão do layout Hive do lago | `"1"` |
| `quantilica.source_id` | Identificador canônico da fonte de dados | `"pdet"` |
| `quantilica.dataset_id` | Identificador do conjunto de dados | `"rais-vinculos"` |
| `quantilica.file_key` | Chave única do arquivo bruto original | `"rais-vinculos_2024-sul"` |
| `quantilica.converted_at` | Carimbo de data/hora da conversão em UTC (ISO 8601) | `"2026-10-27T03:00:00Z"` |
| `quantilica.origin_sha256` | Hash SHA-256 do arquivo bruto de origem | `"a3f1b...8e4"` |
| `quantilica.origin_file` | Nome completo do arquivo original no disco bruto | `"rais-vinculos_2024-sul@20260513.7z"` |
| `quantilica.format_version` | Versão do formato de dados analítico | `"1"` |
| `quantilica.spec_version` | Versão da especificação técnica de dados | `"1"` |
| `quantilica.converter` | Identificador do módulo conversor | `"pdet-fetcher"` |
| `quantilica.writer` | Nome e versão da biblioteca responsável pela escrita | `"quantilica-analytics/0.2.0"` |
| `quantilica.contract.id` | Identificador do contrato de schema (`DataContract`), se houver | `"rais-vinculos"` |
| `quantilica.contract.version` | Versão do contrato de schema aplicado | `"1"` |
| `quantilica.cast_nulls` | Dicionário serializado em JSON com contagem de valores convertidos para nulo via `TRY_CAST` | `{"remuneracao_media": 14}` |

Esses metadados viabilizam auditorias determinísticas de proveniência, validação de frescor e verificação automática de integridade sem a necessidade de ler as linhas de dados.

---

## 4. Descritor `_dataset.json`

O arquivo `_dataset.json` localiza-se na raiz de cada conjunto de dados (`$QUANTILICA_LAKE_DIR/<source_id>/<dataset_id>/_dataset.json`). Ele define a identidade do dataset, as chaves de partição, os tipos de dados declarados para cada partição e o modelo de conversão.

### Estrutura do documento (`layout_version = 1`)

```json
{
  "source_id": "pdet",
  "dataset_id": "rais-vinculos",
  "alias": "pdet_rais_vinculos",
  "layout_version": 1,
  "partition_keys": [
    "ano",
    "regiao"
  ],
  "partition_types": {
    "ano": "int",
    "regiao": "varchar"
  },
  "partition_source": "file",
  "contract_id": "rais-vinculos",
  "contract_version": 1,
  "converter": "pdet-fetcher"
}
```

### Detalhamento dos campos

- `source_id` (*string*): Identificador da fonte coletora.
- `dataset_id` (*string*): Identificador do conjunto de dados específico.
- `alias` (*string*): Identificador amigável em snake_case ASCII utilizado na criação de views automáticas em SQL e DuckDB.
- `layout_version` (*inteiro*): Versão do contrato de layout, atualmente fixado em `1`.
- `partition_keys` (*lista de strings*): Chaves ordenadas que formam a estrutura de diretórios Hive. A ordem da lista reflete a profundidade hierárquica dos diretórios (`k1/k2/...`).
- `partition_types` (*objeto*): Mapeamento entre cada chave de partição e o respectivo tipo lógico declarado (`varchar`, `int`, `bigint`, `date`, `double`, `boolean`). Garante que valores como `mes=09` não sejam interpretados erroneamente como inteiros e percam o zero à esquerda durante a leitura.
- `partition_source` (*string*): Origem das partições. Atualmente `"file"` (partições derivadas da identidade ou nome do arquivo de origem) ou `"rows"` (partições derivadas dos valores das linhas).
- `contract_id` (*string | null*): Identificador do contrato de schema associado ao dataset.
- `contract_version` (*inteiro | null*): Versão do contrato de schema.
- `converter` (*string | null*): Nome do componente de software responsável pela conversão.

O descritor é manipulado e gravado atomicamente por meio da classe `DatasetDescriptor` de `quantilica.core.lake`.

---

## 5. Garantias de Atomicidade e Concorrência (`LakeWriter`)

A escrita no lago é realizada prioritariamente pela classe `LakeWriter` de `quantilica.analytics.lake`, que assegura robustez operacional e integridade transacional contra interrupções de processo e concorrência local.

### 5.1 Escrita temporária e publicação atômica

Todo arquivo Parquet é inicialmente gravado em um subdiretório temporário de trabalho (`.tmp/`) ou com extensão `.tmp`, residindo **obrigatoriamente no mesmo filesystem** do diretório final de destino. Uma vez concluída e verificada a escrita, a publicação para o caminho definitivo é realizada por meio da chamada de sistema `os.replace` (semântica POSIX atômica). Dessa forma, leitores concorrentes nunca encontram arquivos Parquet incompletos ou parcialmente transferidos.

### 5.2 Publicação de arquivos particionados em múltiplas partes

Quando um conjunto de dados é fatiado em múltiplas partes (`-001`, `-002`, ..., `-NNN`), o `LakeWriter` realiza a publicação das partes na **ordem numérica decrescente** (da maior para a menor). Como a validação de integridade (`origin_matches`) exige que as partes formem uma sequência completa a partir de `001`, uma eventual falha no processo de publicação deixa o conjunto em estado incompleto, impedindo que leitores consumam dados parciais e forçando uma reconversão limpa na execução seguinte.

### 5.3 Expurgo de partes órfãs

Caso uma execução anterior tenha gerado quatro partes (`-001` a `-004`) e uma nova execução dos mesmos dados gere apenas duas partes (`-001` e `-002`), o `LakeWriter` apaga automaticamente as partes residuais excedentes (`-003` e `-004`). Isso previne a ocorrência de linhas duplicadas em consultas agregadas subsequentes.

### 5.4 Idempotência estrita

Antes de processar qualquer conversão, o `LakeWriter` inspeciona as partes existentes no diretório de destino por meio da função `origin_matches()`. A escrita é descartada imediatamente (`skipped`) caso:

1. As partes formem uma sequência completa sem lacunas;
2. Todas as partes tenham sido gravadas na mesma execução (`converted_at` idêntico);
3. O hash `origin_sha256`, o `layout_version` e a versão do contrato correspondam aos valores atuais do arquivo bruto.

A flag `--force` permite sobrepor a verificação de frescor e forçar a reconversão integral quando necessário.

### 5.5 Locks cooperativos por conjunto de dados

O acesso de escrita a cada dataset é protegido pelo context manager `dataset_lock(dataset_dir)` (`quantilica.core.lake`). O mecanismo utiliza `fcntl.flock` no modo exclusivo sobre o arquivo `.lock` localizado na raiz do conjunto de dados. Isso assegura que múltiplos processos executando tarefas concorrentes aguardem sua vez sem corromper o diretório. Leitores analíticos não tomam locks e operam de forma não bloqueante.

---

## 6. Interoperabilidade de Motores Analíticos

O Lake Hive do ecossistema Quantilica foi projetado para interoperabilidade fluida entre os principais motores analíticos do ecossistema de dados em Python:

### DuckDB

O DuckDB atua como motor primário de streaming para ingestão e conversão de arquivos volumosos (CSV, TXT, delimitadores customizados, codificações legadas como Latin-1/CP1252 e descompressão de arquivos compactados `.zip` e `.7z`).

- **Leitura**: Deve ser realizada com particionamento Hive ativado e com os tipos das partições expressos conforme declarado no `_dataset.json`:
  ```sql
  SELECT * FROM read_parquet(
      '~/data/lake/pdet/rais-vinculos/**/*.parquet',
      hive_partitioning = true,
      hive_types = {'ano': 'INTEGER', 'regiao': 'VARCHAR'}
  );
  ```
- **Views automatizadas**: O helper `duckdb_view_sql(dataset_dir)` gera o comando `CREATE OR REPLACE VIEW` tipado e formatado automaticamente para qualquer dataset do lago.
- **Escrita em lotes**: Utiliza `COPY (...) TO ... (FORMAT parquet, COMPRESSION zstd, FILE_SIZE_BYTES ...)` para fatiamento de alto desempenho sem saturação de memória RAM.

### Polars

O Polars é utilizado tanto para leitura sob demanda quanto para escrita estruturada de conjuntos manipulados via DataFrames.

- **Leitura**: A função `scan_dataset(dataset_dir)` de `quantilica.analytics.lake` carrega o dataset de forma preguiçosa (*lazy*), aplicando o schema Hive configurado:
  ```python
  from quantilica.analytics.lake import scan_dataset

  lf = scan_dataset(caminho_dataset)
  resultado = lf.filter(pl.col("ano") == 2024).collect()
  ```
- **Escrita**: `LakeWriter.write_polars()` suporta `DataFrame` e `LazyFrame`. Quando o plano de execução permite streaming, utiliza `data.sink_parquet()`, minimizando a pegada de memória do processo.

### PyArrow

O PyArrow oferece compatibilidade total na leitura de datasets particionados via API nativa:

```python
import pyarrow.dataset as pa_ds

particionamento = pa_ds.partitioning(
    schema=pa.schema([("ano", pa.int64()), ("regiao", pa.string())]),
    flavor="hive"
)
dataset = pa_ds.dataset(caminho_dataset, format="parquet", partitioning=particionamento)
total_linhas = dataset.count_rows()
```

---

## 7. Integração com Fetchers e CLI

### 7.1 Registro de Entry Points no `pyproject.toml`

Todo pacote coletor que produz ou alimenta o lake deve registrar seu conversor no grupo de entry points `quantilica.lake`:

```toml
[project.entry-points."quantilica.lake"]
<source_id> = "<modulo>.lake:converter"
```

Exemplo real em `pdet-fetcher/pyproject.toml`:

```toml
[project.entry-points."quantilica.lake"]
pdet = "pdet_fetcher.lake:converter"
```

A descoberta é realizada dinamicamente pelo ecossistema por meio de `quantilica.core.lake.load_lake_converter(source_id)`.

### 7.2 Comandos padronizados no `FetcherApp`

O `FetcherApp` (`quantilica.cli.sdk`) disponibiliza decorators padronizados para integrar os fluxos de conversão à interface CLI dos fetchers:

- `fetcher.command_convert(func)`: Registra o subcomando canônico `convert`. A função associada recebe `(input_dir, lake_dir, dataset=None, force=False)`.
- `fetcher.command_pipeline(func)`: Registra o subcomando canônico `pipeline`. Executa a sincronização de dados brutos (`sync`) no passo 1/2 e dispara a conversão para o lake (`convert`) no passo 2/2.

Exemplo de uso em `plugin.py`:

```python
from quantilica.cli.sdk import FetcherApp

fetcher = FetcherApp(name="pdet-fetcher", help="Microdados do PDET.")

def convert(input_dir: Path, lake_dir: Path, dataset: list[str] | None = None, force: bool = False):
    from pdet_fetcher import lake
    return lake.converter.convert(input_dir, lake_dir, datasets=dataset, force=force)

fetcher.command_convert(convert)
fetcher.command_pipeline(convert)
```

### 7.3 Flags canônicas de conversão

Os subcomandos `convert` e `pipeline` expõem opções homogêneas em todos os coletores do ecossistema:

| Opção | Atalho | Padrão | Descrição |
|---|---|---|---|
| `--input` | `-i` | `/data/<fonte>` | Diretório contendo os arquivos brutos baixados |
| `--lake` | `-o`, `--output` | `lake_root()` | Diretório raiz do Lake Hive |
| `--dataset` | — | `None` (todos) | Filtro de dataset(s) específico(s) a converter (repetível) |
| `--force` | — | `False` | Força a reconversão ignorando hash SHA-256 existente |
| `--verbose` | — | `False` | Habilita saída detalhada de logging e diagnóstico |

### 7.4 Fronteira do módulo `lake.py` e extra opcional

Conforme as normas arquiteturais do ecossistema, os coletores são ferramentas leves de extração. O processamento de dados e a escrita no lake residem obrigatoriamente no módulo `lake.py` do coletor, sob a dependência opcional `[analysis]`.

Caso o usuário invoque `convert` ou `pipeline` sem o extra instalado, a CLI intercepta o `ImportError` e emite uma mensagem com a instrução de instalação adequada (`quantilica install <fonte> --extra analysis`), encerrando com código de saída 1 de maneira limpa.

---

## 8. Verificação e Conformidade (`check_dataset`)

A conformidade de qualquer conjunto de dados no lago pode ser verificada programaticamente com a função `check_dataset` de `quantilica.analytics.lake`:

```python
from quantilica.analytics.lake import check_dataset

inconsistencias = check_dataset(caminho_dataset)
if inconsistencias:
    for erro in inconsistencias:
        print(f"Não conformidade detectada: {erro}")
else:
    print("Dataset 100% conforme com a especificação de Lake Hive.")
```

### Validações executadas

A função `check_dataset` realiza as seguintes auditorias sequenciais:

1. **Validação do descritor**: Verifica a presença, sintaxe JSON e integridade de campos do arquivo `_dataset.json`, bem como a compatibilidade da versão de layout (`layout_version = 1`).
2. **Conformidade da hierarquia Hive**: Percorre a árvore de diretórios conferindo se os níveis atendem ao padrão `chave=valor` na ordem exata definida em `partition_keys`.
3. **Nomenclatura e continuidade das partes Parquet**: Garante que os arquivos sigam a convenção `<file_key>[-NNN].parquet` e que, caso haja múltiplas partes, a numeração seja contígua a partir de `001`.
4. **Metadados de rodapé obrigatórios**: Inspeciona os footers Parquet assegurando a presença de todas as chaves obrigatórias (`quantilica.*`) e a correspondência com o descritor.
5. **Verificação de não redundância de partição**: Confirma que nenhuma das chaves de partição do caminho físico esteja gravada como coluna de dados dentro do Parquet.
6. **Paridade cruzada de motores**: Executa uma leitura completa utilizando DuckDB, Polars e PyArrow, conferindo se todos os três motores reportam exatamente a mesma contagem de linhas e preservam os tipos de partição declarados.

Qualquer discrepância encontrada é retornada como item em uma lista de erros. A lista vazia indica conformidade plena com o padrão.
