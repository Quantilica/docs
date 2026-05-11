---
title: quantilica-io
description: Camada analítica da Quantilica — leitura multi-formato, conversão Parquet tipada e proveniência injetada.
---

# `quantilica-io`

Camada de processamento e padronização analítica da Quantilica. Transforma arquivos brutos baixados pelos coletores em ativos analíticos prontos para consumo — Parquet tipado, com proveniência embarcada no próprio header do arquivo.

> **Por que separado do core?** Porque processamento analítico exige Polars e PyArrow — somando 50 MB+ de dependências binárias. Quem só quer baixar dados não deveria pagar esse preço. A divisão `core` (leve) / `io` (pesado) é deliberada.

## Instalação

```bash
uv add "quantilica-io @ git+https://github.com/Quantilica/quantilica-io.git"
```

## Da bagunça ao Parquet em uma chamada

Você baixou um arquivo com um coletor Quantilica. Ao lado dele há um `.manifest.json`. Para converter para Parquet com proveniência preservada:

```python
from quantilica_core.manifests import DownloadManifest
from quantilica_io.writer import to_parquet

manifest = DownloadManifest.read_json("data/raw/dataset.csv.manifest.json")

to_parquet(manifest, "data/processed/dataset.parquet")
```

O `.parquet` resultante já contém, no próprio header (key-value metadata):

- O SHA-256 do arquivo bruto original.
- A URL de origem e o `producer` que baixou.
- O timestamp do download.
- O schema declarado (se um `DataContract` foi usado).

Isso é **time travel real**: meses depois, você consegue provar exatamente qual versão do dado oficial foi usada em uma análise. Reprodutibilidade que sobrevive a mudanças silenciosas das fontes.

## Recursos

- **Reader multi-formato**: interface unificada para CSV, Excel, DBF (comum no DATASUS) e JSON.
- **Detecção automática de encoding**: `latin-1`, `utf-8`, `windows-1252` — sem ter que adivinhar.
- **Parquet otimizado**: compressão `zstd`, particionamento por metadados do dataset.
- **Data Contracts**: validação preventiva de schema — erro imediato se a fonte oficial alterar o layout.
- **Proveniência injetada**: manifesto do `quantilica-core` embutido no header do Parquet.

## Quando NÃO usar

- Se você só precisa **baixar** um arquivo, fique com [`quantilica-core`](quantilica-core.md). Mais leve, sem Polars.
- Se você já tem um pipeline Polars/Arrow estabelecido e não quer adotar nosso padrão de Parquet — o `to_parquet()` é opinativo de propósito.

## Princípios

1. **Reuso de boilerplate** — a lógica de lidar com `latin-1` e separador `;` do governo brasileiro é escrita **uma vez**.
2. **Interoperabilidade Parquet** — todos os arquivos gerados pela plataforma seguem o mesmo padrão, permitindo SQL via DuckDB sobre múltiplos datasets sem conflito de tipos.
3. **Proveniência embarcada** — o arquivo Parquet é auto-suficiente. Não precisa de um JSON ao lado para provar de onde veio.

Veja também:

- [Parquet + Polars](../concepts/parquet-polars.md) — o porquê do formato.
- [Princípios de Design](../concepts/principios.md) — Reprodutibilidade e Sem Mágica.

## Status

> Em desenvolvimento ativo. A API pode evoluir. Veja o [plano de implementação](https://github.com/Quantilica/.github/blob/main/QUANTILICA_IO_PLAN.md) para detalhes.

## Repositório

[github.com/Quantilica/quantilica-io](https://github.com/Quantilica/quantilica-io) — MIT.
