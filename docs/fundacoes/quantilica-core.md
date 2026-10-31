---
title: quantilica-core
description: Fundação domain-neutral de I/O para todos os coletores e pipelines Quantilica.
---

# `quantilica-core`

Biblioteca de utilitários **domain-neutral** que serve como base para todos os coletores e pipelines Quantilica. Centraliza rede resiliente, armazenamento atômico, proveniência criptográfica e logging estruturado — permitindo que cada pacote de domínio foque exclusivamente na lógica da sua fonte.

> **A regra de ouro é a neutralidade de domínio.** O `quantilica-core` não sabe o que é SIDRA, DATASUS ou Tesouro Nacional. Ele lida exclusivamente com abstrações técnicas (HTTP, FTP, storage, manifestos, logging).

## Instalação

```bash
uv add quantilica-core
```

## Anatomia de um download Quantilica

Os três blocos de construção que todo coletor do ecossistema usa:

```python
from quantilica.core.http import HttpClient
from quantilica.core.storage import LocalStorage
from quantilica.core.manifests import DownloadManifest, write_manifest_sidecar

# 1. HTTP resiliente — retry com backoff exponencial
client = HttpClient(attempts=3)
response = client.get("https://servicodados.ibge.gov.br/api/v3/agregados/1705/metadados")

# 2. Storage atômico — escrita sem deixar arquivo corrompido em caso de falha
storage = LocalStorage("dados/raw")
stat = storage.write_bytes("sidra/agregado-1705.json", response.content)

# 3. Manifesto SHA-256 — proveniência criptográfica do artefato
manifest = DownloadManifest.from_file(
    source_id="ibge",
    dataset_id="sidra-1705",
    url="https://servicodados.ibge.gov.br/...",
    file_path=stat.path,
    producer="sidra-fetcher",
)
write_manifest_sidecar(stat.path, manifest)
```

Resultado em disco:

```
dados/raw/sidra/
├── agregado-1705.json
└── agregado-1705.json.manifest.json    ← schema v2: SHA-256, URL, timestamp, producer, source_meta
```

## Módulos

| Módulo | Responsabilidade |
|---|---|
| `http` | `HttpClient` e `AsyncHttpClient` com retentativas, backoff exponencial e `download_with_manifest` |
| `ftp` | Cliente FTP resiliente para fontes legadas (DATASUS, PDET) com `download_with_manifest` |
| `retry` | Lógica configurável para falhas de rede e erros transientes |
| `storage` | `LocalStorage` e `BaseDataRepository` para artefatos brutos e processados |
| `files` | Escrita atômica, cálculo incremental de SHA-256, descompactação (`decompress_archive`) e validação de payload (`check_payload`) |
| `manifests` | `DownloadManifest` (schema v2, `MANIFEST_VERSION = 2`), `DatasetManifest`, `RunManifest` e helpers de sidecar `.manifest.json` |
| `sync` | Probes de frescor (`HttpFreshnessProbe`, `FtpFreshnessProbe`), políticas de skip (`should_skip`) e validação estrita (`is_manifest_valid`) |
| `lake` | Contrato do Lake Hive (`lake_root`, `file_key`, `DatasetDescriptor`, `select_current`, `materialize_view`) |
| `logging` | `get_logger`, `log_step` — logging estruturado padronizado |
| `exceptions` | Hierarquia comum: `FetchError`, `ParseError`, `StorageError`, `CorruptPayloadError` |

## Manifestos de proveniência (`manifests` — Schema v2)

O módulo `quantilica.core.manifests` define o contrato de proveniência criptográfica na versão `MANIFEST_VERSION = 2`:

- **`DownloadManifest`**: manifesto individual por arquivo baixado (`<arquivo>.manifest.json`). Registra a identidade do recurso (`source_id`, `dataset_id`, `resource_id`, `url`, `path`), integridade (`sha256`, `size_bytes`, `fetched_at`), autoria (`producer`, `producer_version`), `manifest_version = 2` e **5 grupos opcionais de enriquecimento**:
  - `source_meta` (`SourceMetadata`): `etag`, `last_modified`, `published_at`, `expected_cadence`
  - `fingerprint` (`ContentFingerprint`): `content_type`, `schema_hash`, `row_count`, `column_count`, `temporal_extent`, `geographic_extent`
  - `lineage` (`Lineage`): `derived_from`, `pipeline_id`
  - `quality` (`QualitySignals`): `validation_status`, `null_ratio`, `diff_from_previous`
  - `execution` (`ExecutionInfo`): `duration_ms`, `retry_count`, `environment`, `data_license`
- **Helpers de sidecar**: `write_manifest_sidecar(target, manifest)`, `read_manifest_sidecar(target)`, `manifest_sidecar_path(target)` e `is_manifest_valid(manifest_path)` (em `quantilica.core.sync`).
- **Lotes e execuções**: `DatasetManifest` (snapshot de múltiplos `DownloadManifest`) e `RunManifest` / `ExecutionManifest` (rastreamento de início, fim e status de uma execução).

Para a anatomia completa do `.manifest.json` v2, tabelas de campos e exemplos de leitura, enriquecimento e injeção em Parquet, veja [Proveniência & Manifestos](../conceitos/proveniencia.md).

## Por que isso importa

Sem `quantilica-core`, cada fetcher precisaria:

- Escrever seu próprio retry com backoff.
- Lidar com falhas parciais de download (arquivo truncado no disco).
- Inventar um formato de proveniência (e raramente fazer SHA-256).
- Decidir um padrão de logging que ninguém mais segue.

Com o core, esses são problemas resolvidos uma vez para sempre. O fetcher fica enxuto e foca no que é específico da fonte — parsear o XML do Siscomex, navegar o FTP do DATASUS, traduzir o JSON do IBGE.

## Princípios

1. **Neutralidade de domínio** — o core nunca sabe que existe IBGE, DATASUS, INMET.
2. **Leveza** — dependências mínimas no núcleo; integrações pesadas ficam em [`quantilica-analytics`](quantilica-analytics.md).
3. **Estabilidade** — testes automatizados para HTTP, storage, manifestos, FTP, retry e sync.
4. **DX** — APIs tipadas e tratamento de erro consistente em toda a organização.

Veja também os [Princípios de Design](../conceitos/principios.md) do ecossistema como um todo.

## Repositório

[github.com/Quantilica/quantilica-core](https://github.com/Quantilica/quantilica-core) — MIT.
