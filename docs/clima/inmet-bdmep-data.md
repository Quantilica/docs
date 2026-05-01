# inmet-bdmep-data: Historical Weather Station Data from Brazil's INMET

**inmet-bdmep-data** is a Python package to download and process historical meteorological data from INMET's BDMEP (Banco de Dados Meteorológicos para Ensino e Pesquisa — Meteorological Database for Teaching and Research).

## Overview

Access Brazil's official historical weather data with:

- **573+ weather stations** across the country
- **Hourly observations** going back decades
- **30+ meteorological variables**: precipitation, temperature, pressure, humidity, wind, radiation, and more
- **Raw downloads** in INMET's native format

## Installation

```bash
pip install inmet-bdmep-data
# or
uv add inmet-bdmep-data
```

**Requirements:** Python 3.10+

## Quick Start

### Download Raw Data

```python
from inmet_bdmep import fetch

# Fetch raw files for specific years
fetch.download_data(
    years=[2022, 2023],
    dest_dir="./data"
)
```

### Read INMET Data Files

```python
from inmet_bdmep.reader import read_zipfile
import polars as pl

# Read downloaded zip file
df = read_zipfile("inmet-bdmep_2022_20220712.zip")

# Data is a Polars DataFrame with 30+ columns
print(df.schema)
print(df.head())

# Example output:
# ┌────────┬──────────────┬────────────────────┬──────────────────────┐
# │ hora   ┆ precipitacao ┆ pressao_atmosfer… ┆ pressao_atmosfer…    │
# │ ---    ┆ ---          ┆ ---                ┆ ---                  │
# │ u32    ┆ f64          ┆ f64                ┆ f64                  │
# ╞════════╪══════════════╪════════════════════╪══════════════════════╡
# │ 0      ┆ 0.0          ┆ 902.9              ┆ 902.9                │
# │ 1      ┆ 0.0          ┆ 903.4              ┆ 903.4                │
# │ 2      ┆ 0.0          ┆ 903.7              ┆ 903.7                │
# │ 3      ┆ 0.0          ┆ 903.4              ┆ 903.4                │
# │ 4      ┆ 0.0          ┆ 903.2              ┆ 903.2                │
# └────────┴──────────────┴────────────────────┴──────────────────────┘
```

## Data Source

Download historical weather data from INMET's public repository:
- **Portal**: https://portal.inmet.gov.br/dadoshistoricos
- **Available data**: 1979-present (varies by station)
- **Update frequency**: Monthly
- **Format**: Zipped text files with fixed schema

## Available Variables

Each observation includes:

| Variable | Unit | Description |
|----------|------|-------------|
| `hora` | hour | Hour of day (0-23) |
| `precipitacao` | mm | Total precipitation |
| `pressao_atmosferica` | hPa | Atmospheric pressure |
| `pressao_maxima` | hPa | Maximum pressure |
| `pressao_minima` | hPa | Minimum pressure |
| `radiacao` | kJ/m² | Solar radiation |
| `temperatura` | °C | Air temperature |
| `temperatura_maxima` | °C | Maximum temperature |
| `temperatura_minima` | °C | Minimum temperature |
| `temperatura_orvalho` | °C | Dew point temperature |
| `umidade` | % | Relative humidity |
| `umidade_maxima` | % | Maximum humidity |
| `umidade_minima` | % | Minimum humidity |
| `velocidade_vento` | m/s | Wind speed |
| `velocidade_vento_max` | m/s | Maximum wind speed |
| And more... | | 30+ total variables |

## Station Information

Access metadata about weather stations:

```python
from inmet_bdmep import stations

# List all stations
all_stations = stations.get_all()

for station in all_stations:
    print(f"{station.codigo_wmo}: {station.nome}")
    print(f"  Location: {station.latitude}, {station.longitude}")
    print(f"  Altitude: {station.altitude}m")
    print()

# Example:
# A898: BAGÉ
#   Location: -27.388611, -51.215833
#   Altitude: 963.0m
```

## Use Cases

- **Climate research**: Historical weather patterns and trends
- **Agricultural analysis**: Precipitation, temperature, radiation for crop modeling
- **Hydrology**: Rainfall patterns for water resource management
- **Energy planning**: Solar radiation data for renewable energy assessment
- **Environmental studies**: Long-term meteorological trends

## Development

Install for development:

```bash
git clone https://github.com/Quantilica/inmet-bdmep-data.git
cd inmet-bdmep-data
pip install -e .
```

## References

- **INMET**: https://portal.inmet.gov.br/
- **BDMEP Portal**: https://portal.inmet.gov.br/dadoshistoricos
- **Station Codes (WMO)**: https://en.wikipedia.org/wiki/WMO_station_ID

## Learn More

- **[Climate & Environment Overview](index.md)** — All climate data tools
- **[Public Health Data](../saude/index.md)** — Health surveillance systems
- **[Architecture](../architecture/overview.md)** — System design
