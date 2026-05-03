# Climate & Environment

Brazilian meteorological and environmental data from INMET (National Institute of Meteorology).

**inmet-bdmep-data** provides access to Brazil's comprehensive historical weather station network, enabling climate research, agricultural analysis, hydrology studies, and environmental monitoring.

## Overview

INMET's BDMEP (Banco de Dados Meteorológicos para Ensino e Pesquisa — Meteorological Database for Teaching and Research) offers:

- **National coverage** of automatic weather stations (~570+ stations in recent years)
- **Hourly observations** going back to 2000
- **17 core meteorological variables**: precipitation, temperature, pressure, humidity, wind, solar radiation
- **Long-term climate trends** for research and planning

## Tools

### [inmet-bdmep-data](inmet-bdmep-data.md)

Download and analyze historical weather data from Brazil's official meteorological network:

- **Weather Station Network** — National coverage with geographic and altitude metadata per row
- **Hourly Observations** — Records from 2000 onward, refreshed yearly by INMET
- **17 Core Variables** — Precipitation, temperature, pressure, humidity, wind, radiation
- **Easy Integration** — pandas (default) or polars DataFrames
- **Official Source** — Data directly from INMET's public portal

## Use Cases

### Climate Research

Analyze long-term climate patterns, temperature trends, and seasonal variations across Brazil.

### Agricultural Planning & Modeling

Use precipitation and temperature data to inform crop selection, irrigation scheduling, and agricultural risk assessment.

### Hydrology & Water Resources

Analyze rainfall patterns and runoff to inform water resource management, drought planning, and flood prediction.

### Energy Planning

Solar radiation and wind data for renewable energy assessment and grid planning.

### Environmental Impact Assessment

Monitor long-term environmental changes, air quality correlations, and climate variability.

## Available Variables

Each observation row includes:

- **Temperature**: Air (dry-bulb), max, min, dew point (max/min)
- **Precipitation**: Total rainfall (mm)
- **Pressure**: Atmospheric at station level, max, min (mB)
- **Humidity**: Relative, max, min (%)
- **Wind**: Speed (m/s), direction (°), max gust (m/s)
- **Radiation**: Global solar radiation (kJ/m²)

## Station Coverage

All weather stations include:

- WMO (World Meteorological Organization) code
- Geographic coordinates (latitude, longitude)
- Altitude
- Data availability periods

## Learn More

- **[inmet-bdmep-data Documentation](inmet-bdmep-data.md)** — Complete reference
- **[Public Health Data](../saude/index.md)** — Health surveillance systems
- **[Architecture](../architecture/overview.md)** — System design
- **[INMET Official](https://portal.inmet.gov.br/)** — Government source
