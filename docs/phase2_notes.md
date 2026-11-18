# Phase 2 – Data Ingestion, Raw Storage & Containerization

## Project: E-Commerce Order & Delivery Analytics Pipeline

### 1. Data Source

The project uses the Brazilian E-Commerce Public Dataset by Olist.

Five CSV files were selected for the ingestion pipeline:

| Dataset | Records |
|---|---:|
| Customers | 99,441 |
| Orders | 99,441 |
| Order Items | 112,650 |
| Products | 32,951 |
| Product Category Translation | 71 |
| **Total** | **344,554** |

The original CSV files are stored in `data/raw/`. These files remain unchanged and are used as the source for ingestion.

### 2. Data Ingestion Process

A modular Python ingestion script was implemented in `scripts/ingestion.py`.

The script:
- Reads the five selected CSV files.
- Validates the CSV headers against the corresponding raw database tables.
- Calculates a SHA-256 hash for each source file.
- Creates an ingestion batch record to track each execution.
- Loads records into PostgreSQL in batches of 5,000 rows.
- Records the source filename, source row number, ingestion batch ID, and ingestion timestamp.
- Logs execution status, timestamps, record counts, and errors.

The script uses Python's CSV module to preserve the original source values as text during raw ingestion.

### 3. Raw Data Storage

Raw data is stored in two locations:

**A. Original CSV Files**

The original source files are retained in `data/raw/` without modifying their contents.

**B. PostgreSQL Raw Schema**

A separate PostgreSQL schema named `raw` was created to store the ingested data.

It contains five raw data tables and an `ingestion_batches` table for execution tracking.

The raw tables preserve the original CSV columns as text and include ingestion metadata.

The existing processed tables in the `public` schema are kept separate and are not modified by the raw ingestion process.

### 4. Duplicate Prevention and Failure Handling

The ingestion pipeline uses SHA-256 file hashing to identify whether an exact version of a source file has already been successfully loaded.

If the same file version is detected, the script skips it instead of inserting duplicate records.

Each ingestion batch is tracked using one of three statuses:

- `running`: ingestion has started.
- `success`: the file was loaded successfully.
- `failed`: an error occurred during processing.

If a file fails during loading, its current transaction is rolled back and the batch is marked as failed. This allows the error to be recorded without leaving partially loaded rows from that batch.

### 5. Execution Logging and Verification

The ingestion script records execution timestamps, file names, processing status, and row counts.

The five datasets were successfully loaded into PostgreSQL:

| Dataset | Rows Loaded | Status |
|---|---:|---|
| Customers | 99,441 | Success |
| Orders | 99,441 | Success |
| Order Items | 112,650 | Success |
| Products | 32,951 | Success |
| Category Translation | 71 | Success |
| **Total** | **344,554** | **Success** |

The database counts and ingestion batch records were verified using SQL queries.

A subsequent Docker execution confirmed that all five unchanged file versions were correctly skipped, demonstrating duplicate prevention.

### 6. Raw Data Profiling and Quality Issues

A separate profiling script, `scripts/raw_data_profiling.py`, was implemented to inspect the five original datasets.

The profiling checks include missing values, duplicate records, key integrity, invalid values, and selected relationship checks.

The main findings include:

- Missing order approval and delivery timestamps.
- 610 products with missing descriptive fields.
- Two products with missing physical measurements.
- Four products with a weight value of zero.
- One product appears in both the descriptive-missing and physical-missing groups.

These findings were documented in `docs/raw_data_quality_report.md`.

No cleaning or modification was performed on the original raw CSV files during profiling.

### 7. Docker Containerization

The ingestion process was containerized using `Dockerfile.ingestion`, based on the `python:3.11-slim` image.

Docker Compose manages three services:

- `postgres`: PostgreSQL database.
- `pgadmin`: database administration interface.
- `ingestion`: Python ingestion process.

The ingestion service:
- Uses the same Docker Compose network as PostgreSQL.
- Connects to PostgreSQL through the service hostname `postgres`.
- Mounts `data/raw/` as a read-only volume.
- Waits for PostgreSQL to become healthy before starting.

The service was successfully built and executed using Docker Compose.

### 8. Conclusion

Phase 2 established a repeatable ingestion pipeline that preserves original source files, stores raw records in a dedicated PostgreSQL schema, tracks execution batches, prevents duplicate ingestion of unchanged files, and runs inside Docker.

A separate profiling process documents data quality issues before any downstream transformation.

The raw ingestion process is kept separate from the existing processed data and analytics tables.
