# Clima e Ambiente

Dados meteorológicos e ambientais brasileiros do INMET (Instituto Nacional de Meteorologia).

**inmet-bdmep-data** fornece acesso à rede abrangente de estações meteorológicas históricas do Brasil, habilitando pesquisa climática, análise agrícola, estudos de hidrologia e monitoramento ambiental.

## Visão Geral

BDMEP do INMET (Banco de Dados Meteorológicos para Ensino e Pesquisa) oferece:

- **Cobertura nacional** de estações meteorológicas automáticas (~570+ estações em anos recentes)
- **Observações horárias** remontando a 2000
- **17 variáveis meteorológicas principais**: precipitação, temperatura, pressão, umidade, vento, radiação solar
- **Tendências climáticas de longo prazo** para pesquisa e planejamento

## Casos de Uso

### Pesquisa Climática

Analisar padrões climáticos de longo prazo, tendências de temperatura e variações sazonais em todo o Brasil.

### Planejamento e Modelagem Agrícola

Use dados de precipitação e temperatura para informar seleção de culturas, agendamento de irrigação e avaliação de risco agrícola.

### Hidrologia e Recursos Hídricos

Analisar padrões de chuva e escoamento para informar gerenciamento de recursos hídricos, planejamento de secas e predição de inundações.

### Planejamento de Energia

Dados de radiação solar e vento para avaliação de energia renovável e planejamento de rede.

### Avaliação de Impacto Ambiental

Monitorar mudanças ambientais de longo prazo, correlações de qualidade do ar e variabilidade climática.

## Acesso

Acesse dados meteorológicos históricos oficiais do Brasil com:

- **Cobertura nacional** de estações meteorológicas automáticas (~570+ estações em anos recentes)
- **Observações horárias** remontando a 2000
- **Limpo & padronizado**: colunas snake_case, `data_hora` parseado, `-9999` → null
- **Filtros**: UF, código de estação, intervalo de data
- **Export**: Parquet, CSV, ou JSON
- **Engines**: pandas (padrão), polars (opcional)

## Instalação

```bash
pip install git+https://github.com/dankkom/inmet-bdmep-data.git
```

**Requisitos:** Python 3.10+

## CLI

Instala o comando `inmet` com três subcomandos: `fetch`, `read`, `stations`.

### Baixar anos brutos

```bash
# Ano único
inmet fetch 2023 --data-dir ./data

# Intervalo
inmet fetch 2000:2024 --data-dir ./data --workers 8
```

### Ler & exportar

```bash
# Tudo para Parquet
inmet read --data-dir ./data --output all.parquet

# Filtrar por UF e ano, exportar CSV
inmet read --data-dir ./data --years 2022:2023 --uf SP,RJ --output sp_rj.csv --format csv

# Estação única, intervalo de data
inmet read --data-dir ./data --station A701 --start 2020-01-01 --end 2020-12-31 --output a701.parquet
```

### Catálogo de estações

```bash
inmet stations --data-dir ./data --output estacoes.csv
```

## API Python

```python
import inmet_bdmep as inmet
from pathlib import Path

data_dir = Path("./data")

# 1. Buscar zips brutos (em paralelo)
inmet.fetch([2020, 2021, 2022, 2023], data_dir, workers=4)

# 2. Ler com filtros → pandas DataFrame
df = inmet.read(
    data_dir,
    years=[2022, 2023],
    uf=["SP", "RJ", "MG"],
    start="2022-06-01",
    end="2023-05-31",
)

# Temperatura média diária por estado
df["temperatura_ar"].groupby([df["uf"], df["data_hora"].dt.date]).mean()

# 3. Catálogo de estações
stations = inmet.read_stations(data_dir)
print(stations[["codigo_wmo", "estacao", "uf", "latitude", "longitude", "altitude"]])
```

Assistentes de nível inferior também expostos: `inmet.read_zipfile(path, uf=..., station=..., start=..., end=...)`, `inmet.find_zipfiles(data_dir, years)`, `inmet.read_metadata(file)`, `inmet.read_station_data(file)`.

## Fonte de Dados

- **Portal**: https://portal.inmet.gov.br/dadoshistoricos
- **Padrão de URL**: `https://portal.inmet.gov.br/uploads/dadoshistoricos/{year}.zip`
- **Dados disponíveis**: 2000–presente (um zip por ano, atualizado periodicamente)
- **Formato**: CSV por estação (separado por `;`, `latin-1`, `,` decimal, `-9999` nulo) com cabeçalho de metadados de 8 linhas

## Variáveis

| Coluna | Unidade | Descrição |
|--------|---------|-----------|
| `data_hora` | datetime | Timestamp da observação (UTC) |
| `precipitacao` | mm | Precipitação total |
| `pressao_atmosferica` | mB | Pressão ao nível da estação |
| `pressao_atmosferica_maxima` | mB | Pressão máxima na última hora |
| `pressao_atmosferica_minima` | mB | Pressão mínima na última hora |
| `radiacao` | kJ/m² | Radiação solar global |
| `temperatura_ar` | °C | Temperatura de bulbo seco |
| `temperatura_orvalho` | °C | Ponto de orvalho |
| `temperatura_maxima` / `_minima` | °C | Temperatura máx./mín. do ar |
| `temperatura_orvalho_maxima` / `_minima` | °C | Ponto de orvalho máx./mín. |
| `umidade_relativa` | % | Umidade relativa |
| `umidade_relativa_maxima` / `_minima` | % | Umidade relativa máx./mín. |
| `vento_velocidade` | m/s | Velocidade do vento |
| `vento_rajada` | m/s | Rajada de vento |
| `vento_direcao` | ° | Direção do vento |

Metadados da estação por linha unidos automaticamente: `regiao`, `uf`, `estacao`, `codigo_wmo`, `latitude`, `longitude`, `altitude`, `data_fundacao`.

## Casos de Uso

- **Pesquisa climática** — tendências de longo prazo, anomalias
- **Análise agrícola** — precipitação, GDD, radiação
- **Hidrologia** — chuva para modelagem de recursos hídricos
- **Planejamento de energia** — radiação solar, vento para renováveis
- **Estudos ambientais** — meteorologia multi-década

## Desenvolvimento

```bash
git clone https://github.com/Quantilica/inmet-bdmep-data.git
cd inmet-bdmep-data
uv sync
pytest
```

## Referências

- **Portal INMET**: https://portal.inmet.gov.br/
- **Downloads BDMEP**: https://portal.inmet.gov.br/dadoshistoricos
- **IDs de estação WMO**: https://en.wikipedia.org/wiki/WMO_station_ID

## Saiba Mais

- **[Dados de Saúde Pública](../saude/datasus-fetcher.md)** — Sistemas de vigilância em saúde
- **[Arquitetura da Plataforma](../concepts/arquitetura.md)** — Design do sistema
