# inmet-bdmep-data: Historical Weather Station Data from Brazil's INMET

**inmet-bdmep-data** is a Python package to download and process historical meteorological data from INMET's BDMEP (Banco de Dados Meteorológicos para Ensino e Pesquisa — Meteorological Database for Teaching and Research).

## Overview

Access Brazil's official historical weather data with:

- **National coverage** of automatic weather stations (~570+ stations in recent years)
- **Hourly observations** going back to 2000
- **Cleaned & standardized**: snake_case columns, parsed `data_hora`, `-9999` → null
- **Filters**: UF, station code, date range
- **Export**: Parquet, CSV, or JSON
- **Engines**: pandas (default), polars (optional)

## Installation

```bash
pip install git+https://github.com/dankkom/inmet-bdmep-data.git
```

**Requirements:** Python 3.10+

## CLI

Installs the `inmet` command with three subcommands: `fetch`, `read`, `stations`.

### Download raw years

```bash
# Single year
inmet fetch 2023 --data-dir ./data

# Range
inmet fetch 2000:2024 --data-dir ./data --workers 8
```

### Read & export

```bash
# Everything to Parquet
inmet read --data-dir ./data --output all.parquet

# Filter by UF and year, export CSV
inmet read --data-dir ./data --years 2022:2023 --uf SP,RJ --output sp_rj.csv --format csv

# Single station, date range
inmet read --data-dir ./data --station A701 --start 2020-01-01 --end 2020-12-31 --output a701.parquet
```

### Station catalog

```bash
inmet stations --data-dir ./data --output estacoes.csv
```

## Python API

```python
import inmet_bdmep as inmet
from pathlib import Path

data_dir = Path("./data")

# 1. Fetch raw zips (parallel)
inmet.fetch([2020, 2021, 2022, 2023], data_dir, workers=4)

# 2. Read with filters → pandas DataFrame
df = inmet.read(
    data_dir,
    years=[2022, 2023],
    uf=["SP", "RJ", "MG"],
    start="2022-06-01",
    end="2023-05-31",
)

# Daily mean temperature by state
df["temperatura_ar"].groupby([df["uf"], df["data_hora"].dt.date]).mean()

# 3. Station catalog
stations = inmet.read_stations(data_dir)
print(stations[["codigo_wmo", "estacao", "uf", "latitude", "longitude", "altitude"]])
```

Lower-level helpers also exposed: `inmet.read_zipfile(path, uf=..., station=..., start=..., end=...)`, `inmet.find_zipfiles(data_dir, years)`, `inmet.read_metadata(file)`, `inmet.read_station_data(file)`.

## Data Source

- **Portal**: https://portal.inmet.gov.br/dadoshistoricos
- **URL pattern**: `https://portal.inmet.gov.br/uploads/dadoshistoricos/{year}.zip`
- **Available data**: 2000–present (one zip per year, refreshed periodically)
- **Format**: Per-station CSV (`;`-separated, `latin-1`, `,` decimal, `-9999` null) with 8-row metadata header

## Variables

| Column | Unit | Description |
|---|---|---|
| `data_hora` | datetime | Observation timestamp (UTC) |
| `precipitacao` | mm | Total precipitation |
| `pressao_atmosferica` | mB | Pressure at station level |
| `pressao_atmosferica_maxima` | mB | Max pressure in last hour |
| `pressao_atmosferica_minima` | mB | Min pressure in last hour |
| `radiacao` | kJ/m² | Global solar radiation |
| `temperatura_ar` | °C | Dry-bulb air temperature |
| `temperatura_orvalho` | °C | Dew point |
| `temperatura_maxima` / `_minima` | °C | Max/min air temperature |
| `temperatura_orvalho_maxima` / `_minima` | °C | Max/min dew point |
| `umidade_relativa` | % | Relative humidity |
| `umidade_relativa_maxima` / `_minima` | % | Max/min relative humidity |
| `vento_velocidade` | m/s | Wind speed |
| `vento_rajada` | m/s | Wind gust |
| `vento_direcao` | ° | Wind direction |

Per-row station metadata joined automatically: `regiao`, `uf`, `estacao`, `codigo_wmo`, `latitude`, `longitude`, `altitude`, `data_fundacao`.

## Use Cases

- **Climate research** — long-term trends, anomalies
- **Agricultural analysis** — precipitation, GDD, radiation
- **Hydrology** — rainfall for water-resource modeling
- **Energy planning** — solar radiation, wind for renewables
- **Environmental studies** — multi-decade meteorology

## Development

```bash
git clone https://github.com/Quantilica/inmet-bdmep-data.git
cd inmet-bdmep-data
uv sync
pytest
```

## References

- **INMET portal**: https://portal.inmet.gov.br/
- **BDMEP downloads**: https://portal.inmet.gov.br/dadoshistoricos
- **WMO station IDs**: https://en.wikipedia.org/wiki/WMO_station_ID

## Learn More

- **[Climate & Environment Overview](index.md)** — All climate data tools
- **[Public Health Data](../saude/index.md)** — Health surveillance systems
- **[Architecture](../architecture/overview.md)** — System design
