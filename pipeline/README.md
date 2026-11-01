# Pipeline

ETL for the learner analytics system. It reads three CSV files, cleans and validates them, and loads the valid rows into PostgreSQL. Rows that fail validation are written to Parquet files together with the reason they were rejected.

The backend reads the cleaned tables from PostgreSQL. It never reads the CSV or Parquet files.

## Data flow

```
data/raw/*.csv
   │  extract      read every column as text, trim header names
   ▼
transform          trim, normalise case and formats, cast types, drop exact duplicates
   ▼
validate           apply rules → valid rows  |  rejected rows + reject_reason
   │                                                   │
   ▼                                                   ▼
load               INSERT ... ON CONFLICT DO NOTHING   data/rejected/<dataset>/<file-hash>/rejected.parquet
   ▼
PostgreSQL  ◄── read by the backend
```

The datasets run in a fixed order because of foreign keys: **programs → students → academic_performance**. All three run on one connection, so the whole run is a single transaction: if any pipeline fails, nothing is committed.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for PostgreSQL)
- [uv](https://docs.astral.sh/uv/)
- The Python version pinned in `.python-version`. The code uses `except A, B:` without parentheses, which is valid only on Python 3.14 and later.

## Quick start

From the repository root:

```bash
cp .env.example .env          # PowerShell: copy .env.example .env
# edit .env and set DB_PASSWORD

docker compose up -d
docker compose ps             # wait until the db service shows "healthy"
```

Then run the pipeline:

```bash
cd pipeline
uv sync
uv run python src/pipeline/main.py
```

On a fresh database the first run creates the tables (`sql/schemas/*.sql`) and loads everything. Running it again is safe and loads nothing new (see [Idempotency](#idempotency)).

## Configuration

There is **one** `.env` file, at the repository root. Docker Compose and the pipeline both read it (`config.py` loads it from the repo root, so the working directory doesn't matter). Never commit it; commit only `.env.example`.

| Variable | Example | Meaning |
|---|---|---|
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | `change-me` | Database password |
| `DB_NAME` | `student_learning` | Database name (created by the container on first start) |
| `DB_HOST` | `localhost` | Host the pipeline connects to |
| `DB_PORT` | `5433` | Port **on your machine** that Docker publishes. The container's own port is always 5432 |

`5433` is used so the container doesn't clash with a PostgreSQL installed locally on 5432.

## Input files

Place these in `data/raw/`:

| File | Columns |
|---|---|
| `programs.csv` | `program_id, program_name_vi, program_name_en, major_code, program_type, first_cohort_year, last_cohort_year` |
| `students.csv` | `student_id, name, program_id, cohort, academic_status` |
| `academic_performance.csv` | `student_id, academic_year, semester, registered_credits, passed_credits, failed_credits, semester_gpa, cumulative_gpa` |

The data is synthetic. Programs follow NEU's admission lists (K62–K68); students are fictional. Some defects are injected on purpose (duplicates, bad formats, missing values, orphan IDs) so the cleaning and validation steps have something to catch.

## Database tables

Defined in `sql/schemas/` and created automatically, in file-name order (`01_`, `02_`, `03_`).

**programs** — primary key `program_id`

| Column | Type | Notes |
|---|---|---|
| `program_id` | TEXT | NEU admission code, e.g. `7340301`, `EP04`, `POHE4`, `CLC3-05` |
| `program_name_vi`, `program_name_en` | TEXT | |
| `major_code` | TEXT | 7-digit major code (not unique across programs) |
| `program_type` | TEXT | One of `Standard`, `EP`, `POHE`, `CLC`, `TT` |
| `first_cohort_year`, `last_cohort_year` | SMALLINT | First and last enrollment year the program appears in NEU's lists |

**students** — primary key `student_id`, foreign key `program_id → programs`

| Column | Type | Notes |
|---|---|---|
| `student_id` | TEXT | 8 digits, starts with `11` |
| `name` | TEXT | |
| `program_id` | TEXT | |
| `cohort` | SMALLINT | Enrollment year (`K65` in the raw file becomes 2023) |
| `academic_status` | TEXT | `studying`, `graduated` or `suspended` |

**academic_performance** — primary key `(student_id, academic_year, semester)`, foreign key `student_id → students`

| Column | Type | Notes |
|---|---|---|
| `academic_year` | TEXT | `2025-2026` |
| `semester` | SMALLINT | 1 or 2 |
| `registered_credits`, `passed_credits`, `failed_credits` | SMALLINT | passed + failed <= registered |
| `semester_gpa`, `cumulative_gpa` | NUMERIC(3,2) | 4.0 scale |

A student's program name is not stored on `students`; join to `programs` on `program_id`.

## Cleaning and validation

**Transform** (fixes what can be fixed): trims whitespace, converts empty strings to null, normalises case (`Studying` → `studying`, `ep04` → `EP04`), converts batch codes to years (`K65` → 2023), turns `2025/2026` into `2025-2026`, casts numeric columns, and removes exact duplicate rows.

**Validate** (rejects what cannot be fixed). A row can fail several rules; all reasons are joined with `;` in `reject_reason`.

| Dataset | Rejection reasons |
|---|---|
| programs | `missing_program_id`, `duplicate_program_id`, `missing_program_name_vi`, `missing_program_name_en`, `missing_major_code`, `invalid_major_code`, `missing_program_type`, `invalid_program_type`, `missing_first_cohort_year`, `missing_last_cohort_year`, `invalid_cohort_year_range` |
| students | `missing_student_id`, `invalid_student_id`, `duplicate_student_id`, `missing_name`, `missing_program_id`, `unknown_program_id`, `missing_cohort`, `missing_academic_status`, `invalid_academic_status` |
| academic_performance | `missing_student_id`, `unknown_student_id`, `missing_academic_year`, `invalid_academic_year`, `missing_semester`, `invalid_semester`, `duplicate_key`, `missing_*_credits`, `negative_credits`, `credits_mismatch`, `missing_semester_gpa`, `missing_cumulative_gpa`, `semester_gpa_out_of_range`, `cumulative_gpa_out_of_range` |

`unknown_program_id` and `unknown_student_id` are checked against the IDs **already in the database**, not against the CSV. A student whose program was rejected is therefore rejected too, and so are that student's performance rows.

For a key that appears more than once with different values (`duplicate_student_id`, `duplicate_key`), every copy is rejected, because the pipeline cannot tell which one is correct. Exact duplicate rows are not rejected; they are removed in the transform and counted in the `duplicated` column of the summary.

## Rejected rows

Rejected rows are written to:

```
data/rejected/<dataset>/<first 12 chars of the source file's SHA-256>/rejected.parquet
```

Each file holds the **transformed** values (already trimmed and normalised), plus `reject_reason` and `rejected_at`. The folder name identifies the version of the input file, so a changed CSV gets a new folder and an unchanged one overwrites its own. When a rerun rejects nothing, the old file is deleted (the empty folder may remain).

Read them with Polars:

```python
import polars as pl

pl.read_parquet("data/rejected/students/*/rejected.parquet")
```

## Idempotency

Every load uses `INSERT ... ON CONFLICT (<primary key>) DO NOTHING`, so running the pipeline again does not create duplicates. It also means existing rows are **never updated**: if a student's `academic_status` changes in a later file, the old value stays. Switch to `ON CONFLICT ... DO UPDATE` if you need updates.

## Expected result on the sample data

First run on an empty database:

| Pipeline | read | duplicated | rejected | loaded |
|---|---|---|---|---|
| programs | 107 | 0 | 0 | 107 |
| students | 204 | 4 | 7 | 193 |
| academic_performance | 1021 | 8 | 61 | 952 |

Second run: `loaded = 0` and `skipped` equals the previous `loaded`.

The 7 rejected students are 3 with no `program_id`, 2 with the unknown `EP99`, and 2 with no `academic_status`. The 61 rejected performance rows are the rows of those students, 3 orphan student IDs, 3 conflicting duplicate pairs, 8 credit mismatches, 8 missing cumulative GPAs and 4 GPAs outside 0–4.

## Project structure

```
pipeline/
├── sql/schemas/            table definitions, run in file-name order
├── src/pipeline/
│   ├── ingestion/          extract.py          read CSV as text, hash the file
│   ├── transformation/     one module per dataset
│   ├── validation/         validate.py         shared rule engine; one module per dataset
│   ├── loading/            postgres.py         connect, schema creation, inserts
│   │                       parquet.py          rejected-row output
│   ├── pipelines/          runner.py           generic extract → transform → validate → load
│   │                       one module per dataset (wires in the right functions)
│   ├── config.py           environment variables and paths
│   ├── logging_config.py   logging and the summary table
│   └── main.py             entry point: runs the three pipelines in order
└── data/
    ├── raw/                input CSVs
    └── rejected/           rejected rows (generated, not committed)
```

To add a dataset: add a schema file, a transform, a validation module (required columns + rules), a load function, and a small module in `pipelines/` that passes them to `run_pipeline`.

## For backend developers

The three tables above are the contract. They contain only validated rows, so the backend does not need to re-check formats or keys. Suggested read-only role:

```sql
CREATE ROLE backend_ro LOGIN PASSWORD '...';
GRANT SELECT ON programs, students, academic_performance TO backend_ro;
```

Only the pipeline writes to these tables. Create the backend's own tables (indicators, cases, outcomes) separately so a pipeline rerun never touches them.

From another container in the same Compose file, connect to host `db` on port `5432`. From your machine, use `localhost` and `DB_PORT`.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Connection refused / timeout | Docker Desktop isn't running, or the container isn't `healthy` yet (`docker compose ps`) |
| Connects but the tables are empty | `DB_PORT` is `5432`, so the pipeline is talking to a local PostgreSQL instead of the container |
| `password authentication failed` after changing `.env` | The container only reads credentials when its volume is first created. Run `docker compose down -v`, then `up -d` and rerun the pipeline (this deletes the stored data) |
| `canceling statement due to lock timeout` | Another session holds an uncommitted transaction, often an IDE SQL console. Check `pg_stat_activity` and commit, roll back or close it |
| `relation "programs" does not exist` | `sql/schemas/01_create_programs.sql` is missing, or the programs pipeline didn't run first |
| Every student rejected as `unknown_program_id` | The `programs` table is empty |
| `Required environment variable ... is missing` | The root `.env` is missing a value |