---
title: quantilica-core
description: Fundação domain-neutral de I/O para todos os coletores e pipelines Quantilica.
---

# `quantilica-core`

Biblioteca de utilitários **domain-neutral** que serve como base para todos os coletores e pipelines Quantilica. Centraliza rede resiliente, armazenamento atômico, proveniência criptográfica e logging estruturado — permitindo que cada pacote de domínio foque exclusivamente na lógica da sua fonte.

> **A regra de ouro é a neutralidade de domínio.** O `quantilica-core` não sabe o que é SIDRA, DATASUS ou Tesouro Nacional. Ele lida exclusivamente com abstrações técnicas (HTTP, FTP, storage, manifestos, logging).

## Instalação

```bash
uv add "quantilica-core @ git+https://github.com/Quantilica/quantilica-core.git"
```

## Anatomia de um download Quantilica

Os três blocos de construção que todo coletor do ecossistema usa:

```python
from quantilica_core.http import HttpClient
from quantilica_core.storage import LocalStorage
from quantilica_core.manifests import DownloadManifest

# 1. HTTP resiliente — retry com backoff exponencial e jitter
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
manifest.write_json(stat.path.with_suffix(".manifest.json"))
```

Resultado em disco:

```
dados/raw/sidra/
├── agregado-1705.json
└── agregado-1705.manifest.json    ← SHA-256, URL, timestamp, producer
```

## Módulos

| Módulo | Responsabilidade |
|---|---|
| `http` | `HttpClient` e `AsyncHttpClient` com backoff exponencial e jitter |
| `ftp` | Cliente FTP resiliente para fontes legadas (DATASUS, etc.) |
| `retry` | Lógica configurável para falhas de rede e erros transientes |
| `storage` | `LocalStorage` para artefatos brutos e processados, com escrita atômica |
| `manifests` | `DownloadManifest`, `ExecutionManifest` — rastreabilidade SHA-256 |
| `metadata` | `MetadataCatalog`, `Source`, `Dataset` — interoperabilidade entre coletores |
| `logging` | `get_logger`, `log_step` — logging estruturado padronizado |
| `exceptions` | Hierarquia comum: `FetchError`, `ParseError`, `StorageError` |

## Por que isso importa

**Você nunca tem que reimplementar isso.** Sem `quantilica-core`, cada fetcher precisaria:

- Escrever seu próprio retry com backoff.
- Lidar com falhas parciais de download (arquivo truncado no disco).
- Inventar um formato de proveniência (e raramente fazer SHA-256).
- Decidir um padrão de logging que ninguém mais segue.

Com o core, esses são problemas resolvidos uma vez para sempre. O fetcher fica enxuto e foca no que é específico da fonte — parsear o XML do Siscomex, navegar o FTP do DATASUS, traduzir o JSON do IBGE.

## Princípios

1. **Neutralidade de domínio** — o core nunca sabe que existe IBGE, DATASUS, INMET.
2. **Leveza** — dependências mínimas no núcleo; integrações pesadas ficam em [`quantilica-io`](quantilica-io.md).
3. **Estabilidade** — alta cobertura de testes em toda a infraestrutura.
4. **DX** — APIs tipadas e tratamento de erro consistente em toda a organização.

Veja também os [Princípios de Design](../concepts/principios.md) do ecossistema como um todo.

## Repositório

[github.com/Quantilica/quantilica-core](https://github.com/Quantilica/quantilica-core) — MIT.
