# Data Pipelines

Building reliable, automated data workflows.

## What Is a Pipeline?

A sequence of automated steps that move data from source to destination.

```
Pipeline = Extract → Validate → Transform → Load → Expose
```

### Simple Pipeline Example

```python
# EXTRACT: Get data
from sidra_fetcher import SidraClient
client = SidraClient()
gdp = client.fetch(table="1620", variable=116)

# VALIDATE: Check quality
assert len(gdp) > 0, "No data returned"
assert "value" in gdp.columns, "Missing value column"

# TRANSFORM: Process
import polars as pl
gdp = gdp.with_columns([
    pl.col("value").pct_change().alias("growth")
])

# LOAD: Store result
gdp.write_parquet("gdp_analysis.parquet")

# EXPOSE: Make available
print("GDP analysis available at gdp_analysis.parquet")
```

## Pipeline Types

### 1. Batch Pipelines

Run at scheduled intervals (daily, weekly, monthly).

**Example**: Daily unemployment data fetch

```python
# Schedule: Every day at 8 AM
# Run: Fetch yesterday's CAGED data
# Store: Append to PostgreSQL
# Time: 5-10 minutes
```

**Tools**: cron, Airflow, Lambda, Cloud Scheduler

**Pros**:
- Simple to implement
- Easy to debug (predictable schedule)
- Cost-effective (run only when needed)

**Cons**:
- Stale data between runs
- May be overkill for small datasets

### 2. Streaming Pipelines

Process data in real-time as it arrives.

**Example**: Live COVID-19 case monitoring

```python
# Monitor: DATASUS API
# Every: 1 minute
# Check: New cases reported
# Alert: If threshold exceeded
```

**Tools**: Kafka, Spark Streaming, Kinesis, Pub/Sub

**Pros**:
- Real-time alerts possible
- Current view of world

**Cons**:
- Complex infrastructure
- Higher operational cost
- Brazilian government data rarely updates real-time

### 3. Hybrid Pipelines

Batch with real-time components.

**Example**: Daily economic dashboard

```
Batch (Daily):
  Fetch IBGE SIDRA, Treasury, RAIS
  Aggregate and store
  ↓
Real-time (Every minute):
  Stream latest data
  Update dashboard
```

## Pipeline Patterns

### Pattern 1: Extract-Load-Transform

```
Raw Data (unchanged)
    ↓ LOAD
PostgreSQL (raw table)
    ↓ TRANSFORM (on-demand)
Views / Aggregations
    ↓ EXPOSE
Dashboards / Analysis
```

**Pros**: Flexibility, preserves raw data, easy to re-process

**Best for**: Large datasets, evolving analysis

### Pattern 2: Extract-Transform-Load

```
Raw Data (API)
    ↓ TRANSFORM
Clean Data (memory)
    ↓ LOAD
PostgreSQL (processed table)
    ↓ EXPOSE
Dashboards / Analysis
```

**Pros**: Optimized storage, predictable output

**Best for**: Small datasets, stable transformations

### Pattern 3: Data Lake

```
Multiple Sources (APIs, databases)
    ↓ INGEST
Raw Layer (Parquet files in S3)
    ↓ TRANSFORM
Bronze/Silver/Gold layers
    ↓ EXPOSE
Dashboards, ML, Analytics
```

**Pros**: Scalable, flexible, audit trail

**Best for**: Enterprise, multiple data sources, large scale

## Building a Production Pipeline

### Step 1: Define Requirements

```
Data source: IBGE SIDRA table 1620, variable 116
Update frequency: Weekly (IBGE publishes Fridays)
Update lag: 60 days (released Fridays)
Volume: 1000-2000 rows per fetch
History: Keep 20+ years
Quality: Validate schema, check for NULLs, monitor for outliers
Output: PostgreSQL table + Parquet archive
SLA: Data available within 2 hours of publication
```

### Step 2: Error Handling

```python
from sidra_fetcher import SidraClient, SidraTimeoutError
import logging

logger = logging.getLogger(__name__)

try:
    client = SidraClient(max_retries=5, timeout=60)
    gdp = client.fetch(table="1620", variable=116)
    
    # Validate
    if len(gdp) == 0:
        raise ValueError("Empty result from IBGE")
    
    # Process
    gdp.write_parquet("gdp.parquet")
    logger.info(f"Successfully fetched {len(gdp)} rows")
    
except SidraTimeoutError:
    logger.error("IBGE API timeout - will retry tomorrow")
    # Alert on-call team
    
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # Alert on-call team
    raise
```

### Step 3: Monitoring

```python
import polars as pl
from datetime import datetime, timedelta

def check_pipeline_health():
    """Check if pipeline is healthy"""
    
    # Check 1: Recency
    df = pl.read_parquet("gdp.parquet")
    last_date = df["date"].max()
    age = datetime.now() - last_date
    
    if age > timedelta(days=75):  # Expect update within 75 days
        alert(f"Data is {age.days} days old")
    
    # Check 2: Completeness
    expected_quarters = 96  # 24 years
    actual_quarters = len(df)
    
    if actual_quarters < expected_quarters * 0.95:
        alert(f"Missing data: {expected_quarters - actual_quarters} rows")
    
    # Check 3: Quality
    missing_values = df["value"].is_null().sum()
    
    if missing_values > 0:
        alert(f"{missing_values} missing values")
    
    # Check 4: Anomalies
    recent_mean = df.tail(8)["value"].mean()  # Last 2 years
    all_time_mean = df["value"].mean()
    
    change = abs(recent_mean - all_time_mean) / all_time_mean
    if change > 0.50:
        alert(f"Value shifted {change*100:.1f}%")

if __name__ == "__main__":
    check_pipeline_health()
```

### Step 4: Scheduling

**Option 1: cron** (simple, one machine)

```bash
# Run every Friday at 9 AM
0 9 * * 5 /usr/bin/python3 /home/user/fetch_gdp.py

# Log output
0 9 * * 5 /usr/bin/python3 /home/user/fetch_gdp.py >> /var/log/gdp_fetch.log 2>&1
```

**Option 2: Apache Airflow** (complex, distributed)

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

def fetch_gdp():
    from sidra_fetcher import SidraClient
    client = SidraClient()
    gdp = client.fetch(table="1620", variable=116)
    gdp.write_parquet("gdp.parquet")

with DAG(
    "gdp_pipeline",
    schedule_interval="0 9 * * 5",  # Every Friday 9 AM
    start_date=datetime(2024, 1, 1),
    default_args={"retries": 3}
) as dag:
    
    extract = PythonOperator(
        task_id="fetch_gdp",
        python_callable=fetch_gdp
    )
    
    validate = PythonOperator(
        task_id="validate_data",
        python_callable=validate_gdp
    )
    
    load = PythonOperator(
        task_id="load_to_db",
        python_callable=load_to_postgres
    )
    
    extract >> validate >> load
```

## Multi-Source Pipeline

Combining data from multiple Brazilian sources:

```python
import polars as pl
from sidra_fetcher import SidraClient
from tddata import TreasuryClient
from pdet_data import RAISClient

# Extract from multiple sources
sidra = SidraClient()
gdp = sidra.fetch(table="1620", variable=116)

treasury = TreasuryClient()
bonds = treasury.fetch(bond_type="NTN-F")

rais = RAISClient()
employment = rais.aggregate(year=2023, group_by="sector")

# Store each source
gdp.write_parquet("data/gdp.parquet")
bonds.write_parquet("data/bonds.parquet")
employment.write_parquet("data/employment.parquet")

# Load into PostgreSQL
import sqlalchemy as sa

engine = sa.create_engine("postgresql://user:pass@localhost/analytics")

gdp.write_database("gdp", engine, if_exists="replace")
bonds.write_database("bonds", engine, if_exists="replace")
employment.write_database("employment", engine, if_exists="replace")

# Create unified view
with engine.connect() as conn:
    conn.execute("""
    CREATE TABLE macro_data AS
    SELECT 
        g.date,
        g.value as gdp,
        b.yield as bond_yield,
        e.avg_salary
    FROM gdp g
    LEFT JOIN bonds b ON DATE_TRUNC('quarter', g.date) = DATE_TRUNC('quarter', b.date)
    LEFT JOIN employment e ON EXTRACT(YEAR FROM g.date) = e.year
    """)
    conn.commit()
```

## Testing Pipelines

### Unit Tests

```python
import pytest
import polars as pl

def test_fetch_gdp():
    """Test data extraction"""
    from sidra_fetcher import SidraClient
    client = SidraClient()
    
    gdp = client.fetch(table="1620", variable=116)
    
    assert len(gdp) > 0, "Empty result"
    assert "value" in gdp.columns, "Missing value column"
    assert "date" in gdp.columns, "Missing date column"

def test_validate_gdp(gdp_data):
    """Test validation logic"""
    assert (gdp_data["value"] > 0).all(), "Negative values"
    assert gdp_data["value"].is_null().sum() == 0, "Null values"

def test_transform_gdp(gdp_data):
    """Test transformation"""
    gdp_with_growth = gdp_data.with_columns([
        pl.col("value").pct_change().alias("growth")
    ])
    
    assert "growth" in gdp_with_growth.columns
    assert gdp_with_growth["growth"].dtype == pl.Float64
```

### Integration Tests

```python
def test_end_to_end_pipeline(tmp_path):
    """Test full pipeline"""
    from pathlib import Path
    import polars as pl
    
    # Extract
    gdp = fetch_gdp()
    
    # Validate
    assert len(gdp) > 100
    
    # Transform
    gdp = gdp.with_columns([
        pl.col("value").pct_change().alias("growth")
    ])
    
    # Load
    output = tmp_path / "gdp.parquet"
    gdp.write_parquet(output)
    
    # Verify
    loaded = pl.read_parquet(output)
    assert len(loaded) == len(gdp)
    assert "growth" in loaded.columns
```

## Common Pitfalls

### Pitfall 1: Silent Failures

```python
# Bad: Fails silently
try:
    gdp = fetch_data()
except:
    gdp = pd.DataFrame()  # Empty result
    
# Good: Log and alert
try:
    gdp = fetch_data()
except Exception as e:
    logger.error(f"Failed to fetch: {e}")
    alert_team()
    raise
```

### Pitfall 2: No Error Handling

```python
# Bad: One failure breaks everything
gdp = fetch_gdp()  # Might fail
bonds = fetch_bonds()  # Won't run if gdp fails
employment = fetch_employment()  # Won't run

# Good: Handle each independently
sources = {
    "gdp": fetch_gdp,
    "bonds": fetch_bonds,
    "employment": fetch_employment
}

results = {}
for name, fetch_fn in sources.items():
    try:
        results[name] = fetch_fn()
    except Exception as e:
        logger.error(f"Failed to fetch {name}: {e}")
        # Continue with other sources
```

### Pitfall 3: No Data Validation

```python
# Bad: Trust the API
gdp = fetch_data()
gdp.write_parquet("gdp.parquet")  # What if API returned garbage?

# Good: Validate before storing
gdp = fetch_data()

if len(gdp) == 0:
    raise ValueError("Empty result")
if gdp["value"].is_null().sum() > 0.5 * len(gdp):
    raise ValueError("Too many nulls")

gdp.write_parquet("gdp.parquet")
```

## See Also

- [Data Engineering](data-engineering.md)
- [Storage](storage.md)
- [Architecture Overview](../architecture/overview.md)
