---
title: Proveniência & Manifestos
description: Como a Quantilica garante reprodutibilidade de longo prazo via manifestos SHA-256 (schema v2), time travel e proveniência embarcada em Parquet.
---

# Proveniência & Manifestos

> Dados públicos brasileiros são vivos. Eles são revisados, republicados, corrigidos — às vezes silenciosamente. Sem proveniência criptográfica, nenhuma análise sobrevive ao seu próprio aniversário.

Toda ferramenta Quantilica que baixa um arquivo também escreve, ao lado, um **manifesto sidecar** (`<arquivo>.manifest.json`) — um JSON com o hash SHA-256, a URL de origem, o carimbo de tempo, a identificação do coletor (*producer*) e metadados da fonte. É o mecanismo que sustenta três compromissos:

- **Preservação histórica ("nada se apaga")**: arquivos brutos são gravados com o carimbo `@timestamp` da publicação oficial em regime *append-only* — republicações governamentais geram novos arquivos ao lado dos antigos, sem jamais sobrescrever ou apagar versões históricas.
- **Reprodutibilidade**: você consegue provar exatamente qual versão de um dado oficial alimentou uma análise.
- **Detecção de mudança silenciosa**: você sabe quando um órgão público republicou um arquivo sem mudar o nome.
- **Verificação de frescor sem re-download**: o coletor compara `ETag`, `Last-Modified` e tamanho registrados no manifesto com o servidor remoto antes de transferir bytes novamente.

## A anatomia de um manifesto (Schema v2)

Para cada artefato bruto baixado (ex.: `exp_2024@20240315.csv`), existe um sidecar `<arquivo>.manifest.json` no **schema v2** (`MANIFEST_VERSION = 2` em `quantilica.core.manifests`):

```json
{
  "dataset_id": "exp",
  "execution": null,
  "fetched_at": "2026-05-10T14:23:01Z",
  "fingerprint": null,
  "lineage": null,
  "manifest_version": 2,
  "metadata": {},
  "path": "/data/comex/exp/exp_2024@20240315.csv",
  "producer": "comex-fetcher",
  "producer_version": "0.4.0",
  "quality": null,
  "resource_id": null,
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "size_bytes": 184520910,
  "source_id": "comex",
  "source_meta": {
    "etag": "\"65f41a-2b10c\"",
    "expected_cadence": null,
    "last_modified": "Fri, 15 Mar 2024 12:00:00 GMT",
    "published_at": null
  },
  "url": "https://balanca.economia.gov.br/balanca/bd/comexstat-bd/ncm/EXP_2024.csv"
}
```

### Campos nucleares (`DownloadManifest`)

| Campo | Tipo | Obrigatoriedade | Descrição |
|---|---|---|---|
| `manifest_version` | `int` | Sempre presente (`2`) | Versão do schema do manifesto (`MANIFEST_VERSION = 2`). Leitores tratam a ausência do campo como versão `1`. |
| `source_id` | `str` | Obrigatório | Identificador canônico da fonte (ex.: `"ibge"`, `"comex"`, `"datasus"`). |
| `dataset_id` | `str` | Obrigatório | Identificador do dataset dentro da fonte (ex.: `"exp"`, `"sih-rd"`). |
| `url` | `str` | Obrigatório | URL HTTP/HTTPS ou caminho FTP exato de onde o artefato foi obtido. |
| `fetched_at` | `str` | Obrigatório | Timestamp UTC em formato ISO-8601 do momento da coleta. |
| `sha256` | `str` | Obrigatório | Digest hexadecimal SHA-256 calculado sobre os bytes do arquivo bruto. |
| `size_bytes` | `int` | Obrigatório | Tamanho exato do arquivo em bytes. |
| `resource_id` | `str \| None` | Opcional | Identificador específico do recurso ou partição quando distinto de `dataset_id`. |
| `path` | `str \| None` | Opcional | Caminho do arquivo bruto gravado em disco. |
| `producer` | `str \| None` | Opcional | Nome do pacote ou ferramenta que realizou a coleta (ex.: `"sidra-fetcher"`). |
| `producer_version` | `str \| None` | Opcional | Versão do pacote coletor no momento da execução. |
| `metadata` | `dict[str, Any]` | Opcional (`{}`) | Dicionário livre para metadados específicos da fonte. |

### Grupos de enriquecimento da v2

Além dos campos nucleares, o `DownloadManifest` v2 define **5 grupos opcionais** (dataclasses imutáveis em `quantilica.core.manifests`). Eles permitem acoplar metadados do servidor, resumo estrutural, linhagem, qualidade e telemetria sem quebrar consumidores que leem apenas o núcleo:

| Campo no JSON | Dataclass (`quantilica.core.manifests`) | Atributos | Finalidade |
|---|---|---|---|
| `source_meta` | `SourceMetadata` | `etag`, `last_modified`, `published_at`, `expected_cadence` | Metadados informados pelo servidor de origem. `HttpClient.download_with_manifest` preenche `etag` e `last_modified` automaticamente a partir dos cabeçalhos HTTP. |
| `fingerprint` | `ContentFingerprint` | `content_type`, `schema_hash`, `row_count`, `column_count`, `temporal_extent`, `geographic_extent` | Impressão digital estrutural do conteúdo (formato, hash das colunas/tipos, contagem de linhas/colunas e cobertura temporal/geográfica) para detectar mudanças estruturais sem diff completo. |
| `lineage` | `Lineage` | `derived_from` (`list[str]`), `pipeline_id` | Rastreabilidade de linhagem: hashes SHA-256 dos artefatos de entrada dos quais o arquivo deriva e identificador do pipeline transformador. |
| `quality` | `QualitySignals` | `validation_status`, `null_ratio`, `diff_from_previous` | Sinais de qualidade calculados na ingestão (status de validação, proporção de nulos e resumo de linhas adicionadas/removidas em relação à versão anterior). |
| `execution` | `ExecutionInfo` | `duration_ms`, `retry_count`, `environment`, `data_license` | Contexto operacional e de reprodutibilidade (tempo de download em ms, número de retentativas, dados do ambiente e licença do dado). |

> **Comportamento de leitura (`read_json` e `read_manifest_sidecar`):** Ao reconstruir um `DownloadManifest` a partir do disco via `DownloadManifest.read_json()` ou `read_manifest_sidecar()`, o `quantilica-core` restaura os campos nucleares de proveniência e o grupo `source_meta` (`etag` e `last_modified`), necessários para verificação de integridade e checagem de frescor HTTP. Os demais grupos analíticos (`fingerprint`, `lineage`, `quality`, `execution`) são ignorados na desserialização leve do core.

## Escrevendo e enriquecendo um manifesto

O comando `sync` dos coletores baseados em `FetcherApp` (bem como `HttpClient.download_with_manifest` e `FtpClient.download_with_manifest`) valida o arquivo baixado e emite o sidecar `.manifest.json` automaticamente.

Para construir um manifesto programaticamente — a partir de um arquivo em disco (`from_file`), de bytes em memória (`from_content`) ou de um hash já calculado em streaming (`from_digest`) — e enriquecê-lo com metadados da v2:

```python
from dataclasses import replace
from quantilica.core.manifests import (
    ContentFingerprint,
    DownloadManifest,
    SourceMetadata,
    write_manifest_sidecar,
)

manifest = DownloadManifest.from_file(
    source_id="ibge",
    dataset_id="sidra-1705",
    url="https://servicodados.ibge.gov.br/api/v3/agregados/1705/metadados",
    file_path="dados/raw/sidra/agregado-1705.json",
    producer="sidra-fetcher",
)

# Como DownloadManifest é frozen=True, use dataclasses.replace para enriquecer:
manifest = replace(
    manifest,
    source_meta=SourceMetadata(
        etag='"W/1a2b3c"',
        expected_cadence="monthly",
    ),
    fingerprint=ContentFingerprint(
        content_type="application/json",
        temporal_extent=["2012-01", "2020-03"],
    ),
)

# Escrita atômica em "dados/raw/sidra/agregado-1705.json.manifest.json"
sidecar_path = write_manifest_sidecar("dados/raw/sidra/agregado-1705.json", manifest)
```

## Lendo um manifesto e verificando integridade

Em vez de abrir o JSON e recalcular hashes manualmente, use os utilitários de `quantilica.core.manifests` e `quantilica.core.sync`:

```python
from pathlib import Path
from quantilica.core.manifests import manifest_sidecar_path, read_manifest_sidecar
from quantilica.core.sync import is_manifest_valid

target = Path("dados/raw/sidra/agregado-1705.json")

# 1. Leitura tolerante a falhas (retorna None se ausente ou corrompido)
manifest = read_manifest_sidecar(target)
if manifest is not None:
    print(manifest.sha256, manifest.manifest_version)

# 2. Validação estrita: confere se o arquivo existe e se tamanho + SHA-256 batem
sidecar = manifest_sidecar_path(target)
if is_manifest_valid(sidecar):
    print("Arquivo íntegro.")
else:
    print("Arquivo ausente ou hash divergente — re-baixe.")
```

### Frescor via sidecar (`source_meta`)

A diretriz padrão do ecossistema é preservar permanentemente todos os arquivos brutos (`@timestamp`) ao lado de seus manifestos ("nada se apaga"). Adicionalmente, quando `HttpClient.download_with_manifest` ou `HttpClient.is_remote_more_recent` verificam se um recurso precisa ser baixado em ambientes intermediários onde apenas o sidecar `<arquivo>.manifest.json` permanece no diretório local após transferência para um arquivo definitivo, o cliente compara o `ETag` (`source_meta.etag`), o `Last-Modified` (`source_meta.last_modified`) e o `Content-Length` (`size_bytes`) com o servidor remoto e evita o re-download quando a origem não mudou.

## Manifestos de catálogo e de execução (`DatasetManifest` e `RunManifest`)

Além do `DownloadManifest` (um por arquivo), o módulo `quantilica.core.manifests` oferece duas estruturas complementares para agrupar lotes e registrar execuções:

- **`DatasetManifest`**: agrega uma coleção de `DownloadManifest` em um snapshot de dataset (`DatasetManifest.create(source_id=..., dataset_id=..., resources=[...])`).
- **`RunManifest`** (também exportado pelo alias `ExecutionManifest`): registra o ciclo de vida de uma execução de coleta ou processamento (`run = RunManifest.start(run_id=..., source_id=...)` → `run = run.finish(status="success")`). Não é exigido por arquivo baixado nos fetchers ([Padronização de CLI](../normas/cli-fetchers.md#14-manifests-de-proveniência--o-que-é-exigido-de-fetchers)).

## Time travel: reproduzindo uma análise passada

O caso clássico: você publicou um relatório em janeiro de 2024 usando uma versão do PIB do IBGE. Em 2026, alguém pede para reproduzir o número exato — mas o IBGE revisou a série no meio.

Com proveniência embarcada, isso é determinístico:

```python
from quantilica.core.manifests import DownloadManifest

# Você guardou o manifesto da análise original
manifest = DownloadManifest.read_json("relatorio-2024/pib.csv.manifest.json")

# A versão exata que alimentou a análise
print(manifest.sha256)      # 'e3b0c4...'
print(manifest.fetched_at)  # '2024-01-15T...'
print(manifest.url)         # endpoint exato + parâmetros
```

Para análises críticas, **versionar o `.manifest.json` no git** ao lado do código é suficiente. O arquivo bruto pode estar em qualquer storage; o manifesto é a fonte de verdade.

## Proveniência embarcada em Parquet e no Lake Hive

O [`quantilica-analytics`](../fundacoes/quantilica-analytics.md) leva a ideia um passo adiante: ao converter um arquivo bruto para Parquet (via `to_parquet` ou `LakeWriter`), ele injeta os dados do manifesto no **header key-value do próprio arquivo Parquet** sob o prefixo `quantilica.*`:

```python
import polars as pl
from quantilica.core.manifests import read_manifest_sidecar
from quantilica.analytics.writer import to_parquet

raw_path = "dados/raw/dataset.csv"
manifest = read_manifest_sidecar(raw_path)

df = pl.read_csv(raw_path)
to_parquet(df, "dados/processed/dataset.parquet", manifest=manifest)
```

O `dataset.parquet` resultante é auto-suficiente: meses depois, qualquer leitor compatível com PyArrow consegue extrair de onde veio aquele dado, sem depender de arquivos vizinhos.

```python
import pyarrow.parquet as pq

pf = pq.ParquetFile("dados/processed/dataset.parquet")
meta = {k.decode(): v.decode() for k, v in pf.metadata.metadata.items()}
print(meta)
# {'quantilica.source_id': 'ibge', 'quantilica.origin_sha256': 'e3b0c4...', ...}
```

Na camada de [Lake Hive](../normas/lake.md), a função `select_current()` de `quantilica.core.lake` também consome o sidecar `.manifest.json` para obter o `sha256` de cada arquivo bruto sem precisar reler gigabytes do disco durante a seleção da versão vigente.

## Detecção de mudança silenciosa

Quando você re-roda um pipeline e o `sha256` do novo download não bate com o do manifesto antigo, **algo mudou na fonte oficial** — mesmo que o nome do arquivo seja o mesmo. Isso é precioso para:

- **Auditoria**: ter prova de que uma análise foi feita com dado X, não com dado X' revisado depois.
- **Alertas**: pipelines podem disparar warning quando um arquivo "estável" muda.
- **Confiança**: pesquisa acadêmica e relatório regulatório precisam dessa garantia para serem defensáveis.

## Padrões relacionados

- **[Princípios de Design — Reprodutibilidade](principios.md#reprodutibilidade)** — o princípio que justifica esse desenho.
- **[Convenções de Armazenamento](storage.md#manifesto-de-proveniência-v2-downloadmanifest-e-dataset_id)** — layout de pastas e sidecar `.manifest.json` nos coletores.
- **[Padronização de Lake Hive](../normas/lake.md)** — como a proveniência do manifesto é propagada para os metadados `quantilica.*` do Parquet e para `_dataset.json`.
- **[`quantilica-core`](../fundacoes/quantilica-core.md)** — onde os manifestos e validadores vivem.
- **[`quantilica-analytics`](../fundacoes/quantilica-analytics.md)** — injeção de proveniência em Parquet.
- **[`sidra-sql`](../fontes/ibge/sidra-sql.md)** — proveniência em nível de linha via SCD Type II no warehouse.
