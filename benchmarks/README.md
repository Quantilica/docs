# Medições do site

Tudo o que o site afirma com número de tamanho ou de tempo vem daqui. Cada script grava um JSON em `data/` com a data, a máquina e as versões. Nenhum valor do site é "ilustrativo": se um número não tem JSON aqui, ele não deveria estar no site.

| Afirmação do site | Script | Dados |
|---|---|---|
| CSV × Parquet: tamanhos e tempos de leitura | `measure_formats.py` | `data/results.json` |
| Gráficos `compression_comparison.svg` e `read_performance.svg` | `charts.py` | `data/results.json` |
| Ganho de baixar em paralelo (threads) | `measure_downloads.py` | `data/downloads.json` |
| Reuso de conexão e `AsyncSidraClient` × `SidraClient` | `measure_sidra_connections.py` | `data/sidra-connections.json` |
| Tamanho da base de CNPJ, compactada e descompactada | `measure_remote_zip.py` | `data/cnpj-2026-09.json` |
| Tamanho e linhas da RAIS | comandos abaixo | `data/rais-2024.json` |
| Estações do INMET | comandos abaixo | `data/inmet-2025.json` |
| Séries do SGS | comandos abaixo | `data/sgs-catalogo.json` |

## Como repetir

Rode da raiz do workspace, onde os fetchers estão instalados (`uv sync --all-packages`).

```bash
# Dados de entrada, no layout que measure_formats.py espera em <dados>/
quantilica td sync taxas-dos-titulos-ofertados-pelo-tesouro-direto -o <dados>/td
#   <dados>/caged/CAGEDMOV202608.txt     <- 7z x do arquivo baixado por: quantilica pdet sync caged-2020-mov
#   <dados>/rais/RAIS_VINC_PUB_CENTRO_OESTE.COMT  <- 7z x do arquivo de 2024 (o script também aceita o do Norte)

uv run --with pandas --with pyarrow python docs/benchmarks/measure_formats.py \
    --data-dir <dados> --out docs/benchmarks/data/results.json
uv run --with matplotlib --with numpy python docs/benchmarks/charts.py

uv run python docs/benchmarks/measure_downloads.py   --out docs/benchmarks/data/downloads.json
uv run python docs/benchmarks/measure_sidra_connections.py --out docs/benchmarks/data/sidra-connections.json
```

Tamanho descompactado de um ZIP remoto, sem baixá-lo (lê só o fim do arquivo por `Range`):

```bash
uv run python -I docs/benchmarks/measure_remote_zip.py urls.json saida.json 8
# urls.json: [["https://.../Arquivo.zip", 123], ...]  (o segundo item é ignorado)
```

RAIS e CAGED (baixados pelo `pdet-fetcher`): linhas e bytes do CSV em streaming, sem gravar o CSV:

```bash
7z l RAIS_VINC_PUB_SP.7z                       # tamanho descompactado
7z x -so -bd RAIS_VINC_PUB_SP.7z | wc -lc      # bytes e quebras de linha (inclui o cabeçalho)
```

## Regras

- **Mediana**, depois de uma rodada de aquecimento. Os tempos de leitura valem com o arquivo no cache de página do sistema operacional e para a máquina registrada em `environment`.
- **Leitores do ecossistema.** O "leitor tipado" é o do próprio fetcher (`read_prices`, `read_caged`, `read_rais`), com a conversão de tipos que o usuário recebe.
- **Parquet.** `DataFrame.write_parquet` com o codec padrão do Polars (`zstd`), o mesmo que `quantilica.analytics.writer.to_parquet` usa. O `snappy` é medido à parte.
- **Rede.** Os tempos de download dependem do servidor e do horário. Repita antes de citar.
- Datas em ISO 8601; tamanhos em bytes nos JSON e em MiB/GiB nos gráficos.
