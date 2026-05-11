---
title: Proveniência & Manifestos
description: Como a Quantilica garante reprodutibilidade de longo prazo via manifestos SHA-256, time travel e proveniência embarcada em Parquet.
---

# Proveniência & Manifestos

> Dados públicos brasileiros são vivos. Eles são revisados, republicados, corrigidos — às vezes de forma silenciosa. Sem proveniência criptográfica, nenhuma análise sobrevive ao seu próprio aniversário.

Toda ferramenta Quantilica que baixa um arquivo também escreve, ao lado, um **manifesto** — um JSON pequeno com SHA-256, URL de origem, timestamp e o nome do *producer*. É o mecanismo que sustenta dois compromissos:

- **Reprodutibilidade**: você consegue provar exatamente qual versão de um dado oficial alimentou uma análise.
- **Detecção de mudança**: você sabe quando o governo republicou um arquivo silenciosamente.

## A anatomia de um manifesto

Para cada `dataset.csv` baixado, existe um `dataset.csv.manifest.json`:

```json
{
  "source_id": "ibge",
  "dataset_id": "sidra-1705",
  "url": "https://servicodados.ibge.gov.br/api/v3/agregados/1705/metadados",
  "filename": "agregado-1705.json",
  "size_bytes": 27843,
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "downloaded_at": "2026-05-10T14:23:01.392Z",
  "producer": "sidra-fetcher",
  "producer_version": "1.2.0"
}
```

Nada de mágico. É um par `(arquivo, hash)` carimbado com tempo e origem.

## Escrevendo um manifesto

```python
from quantilica_core.http import HttpClient
from quantilica_core.storage import LocalStorage
from quantilica_core.manifests import DownloadManifest

client = HttpClient(attempts=3)
storage = LocalStorage("dados/raw")

response = client.get("https://servicodados.ibge.gov.br/api/v3/agregados/1705/metadados")
stat = storage.write_bytes("sidra/agregado-1705.json", response.content)

manifest = DownloadManifest.from_file(
    source_id="ibge",
    dataset_id="sidra-1705",
    url="https://servicodados.ibge.gov.br/api/v3/agregados/1705/metadados",
    file_path=stat.path,
    producer="sidra-fetcher",
)
manifest.write_json(stat.path.with_suffix(".manifest.json"))
```

A maioria dos coletores Quantilica faz isso por baixo dos panos — você não precisa montar o manifesto à mão.

## Lendo um manifesto para verificar integridade

```python
from quantilica_core.manifests import DownloadManifest

manifest = DownloadManifest.read_json("dados/raw/sidra/agregado-1705.manifest.json")

if manifest.verify("dados/raw/sidra/agregado-1705.json"):
    print("Arquivo íntegro.")
else:
    print("Hash mudou — re-baixe.")
```

## Time travel: reproduzindo uma análise passada

O caso clássico: você publicou um relatório em janeiro de 2024 usando uma versão do PIB do IBGE. Em 2026, alguém pede para reproduzir o número exato — mas o IBGE revisou a série no meio.

Com proveniência embarcada, isso é determinístico:

```python
from quantilica_io.writer import to_parquet
from quantilica_core.manifests import DownloadManifest

# Você guardou o manifesto da análise original
manifest = DownloadManifest.read_json("relatorio-2024/pib.csv.manifest.json")

# A versão exata que alimentou a análise
print(manifest.sha256)        # 'e3b0c4...'
print(manifest.downloaded_at) # '2024-01-15T...'
print(manifest.url)           # endpoint exato + parâmetros

# Re-baixe se quiser, ou apenas confirme que o arquivo no disco bate
```

Para análises críticas, **versionar o `.manifest.json` no git** ao lado do código é suficiente. O arquivo bruto pode estar em qualquer storage; o manifesto é a fonte de verdade.

## Proveniência embarcada em Parquet

O [`quantilica-io`](../fundacoes/quantilica-io.md) leva a ideia um passo adiante: ao converter para Parquet, ele injeta o manifesto no **header key-value do próprio arquivo**.

```python
from quantilica_core.manifests import DownloadManifest
from quantilica_io.writer import to_parquet

manifest = DownloadManifest.read_json("dados/raw/dataset.csv.manifest.json")
to_parquet(manifest, "dados/processed/dataset.parquet")
```

O `dataset.parquet` resultante é auto-suficiente: meses depois, qualquer leitor compatível com PyArrow consegue extrair de onde veio aquele dado, sem depender de arquivos vizinhos.

```python
import pyarrow.parquet as pq

table = pq.read_table("dados/processed/dataset.parquet")
print(table.schema.metadata)
# {b'quantilica.source_id': b'ibge', b'quantilica.sha256': b'e3b0c4...', ...}
```

## Detecção de mudança silenciosa

Quando você re-roda um pipeline e o `sha256` do novo download não bate com o do manifesto antigo, **algo mudou na fonte oficial** — mesmo que o nome do arquivo seja o mesmo. Isso é precioso para:

- **Auditoria**: ter prova de que uma análise foi feita com dado X, não com dado X' revisado depois.
- **Alertas**: pipelines podem disparar warning quando um arquivo "estável" muda.
- **Confiança**: pesquisa acadêmica e relatório regulatório precisam dessa garantia para serem defensáveis.

## Padrões relacionados

- **[Princípios de Design — Reprodutibilidade](principios.md#reprodutibilidade)** — o princípio que justifica esse desenho.
- **[`quantilica-core`](../fundacoes/quantilica-core.md)** — onde os manifestos vivem.
- **[`quantilica-io`](../fundacoes/quantilica-io.md)** — injeção em Parquet.
- **[`sidra-sql`](../ibge/sidra-sql.md)** — proveniência em nível de linha via SCD Type II no warehouse.
