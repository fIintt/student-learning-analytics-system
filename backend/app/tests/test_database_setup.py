"""Kiểm tra backend và bảng pipeline trên PostgreSQL thật."""

import re
from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.db.session import PIPELINE_TABLES, Base, init_db, make_engine

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "pipeline" / "sql" / "schemas"


def test_engine_rejects_other_database_backends():
    with pytest.raises(ValueError, match="chỉ hỗ trợ PostgreSQL"):
        make_engine("mysql://localhost/test")


def test_plain_postgresql_url_uses_psycopg():
    engine = make_engine("postgresql://localhost/test")
    try:
        assert engine.dialect.name == "postgresql"
        assert engine.dialect.driver == "psycopg"
    finally:
        engine.dispose()


def _own_tables():
    import app.models  # noqa: F401

    return [t for t in Base.metadata.sorted_tables if not t.info.get("pipeline")]


def _pipeline_tables():
    import app.models  # noqa: F401

    return [t for t in Base.metadata.sorted_tables if t.info.get("pipeline")]


def test_pipeline_tables_are_flagged_and_complete():
    assert sorted(t.name for t in _pipeline_tables()) == sorted(PIPELINE_TABLES)
    assert not {t.name for t in _own_tables()} & set(PIPELINE_TABLES)


def test_ddl_compiles_for_postgresql():
    for table in _own_tables():
        ddl = str(CreateTable(table).compile(dialect=postgresql.dialect()))
        assert table.name in ddl


@pytest.mark.skipif(not SCHEMA_DIR.exists(), reason="Không có thư mục pipeline/sql/schemas")
def test_models_match_pipeline_sql_schemas():
    """Model chỉ đọc phải khớp tên bảng, tên cột và khoá chính trong file SQL của pipeline."""
    tables = {t.name: t for t in _pipeline_tables()}
    seen = set()
    for sql_file in sorted(SCHEMA_DIR.glob("*.sql")):
        text = sql_file.read_text(encoding="utf-8")
        name = re.search(r"CREATE TABLE IF NOT EXISTS (\w+)", text).group(1)
        if name not in tables:
            continue  # bảng pipeline mà backend chưa đọc (staff, accounts)
        columns = set(re.findall(r"^\s{4}(\w+)\s+(?:TEXT|SMALLINT|NUMERIC|INTEGER)", text, flags=re.M))
        inline_pk = set(re.findall(r"^\s{4}(\w+)\s+TEXT PRIMARY KEY", text, flags=re.M))
        table_pk = re.search(r"PRIMARY KEY \(([^)]+)\)", text)
        primary_key = inline_pk or {c.strip() for c in table_pk.group(1).split(",")}

        model = tables[name]
        assert set(model.columns.keys()) == columns, f"{name}: cột không khớp {sql_file.name}"
        assert {c.name for c in model.primary_key.columns} == primary_key, f"{name}: khoá chính không khớp"
        seen.add(name)
    assert seen == set(PIPELINE_TABLES)


def test_init_db_requires_pipeline_tables(empty_engine):
    engine = empty_engine
    with pytest.raises(RuntimeError, match="Chưa có bảng của pipeline"):
        init_db(engine)
    assert inspect(engine).get_table_names() == []   # không tạo gì khi thiếu bảng của pipeline


def test_init_db_creates_only_backend_tables(empty_engine):
    engine = empty_engine
    Base.metadata.create_all(engine, tables=_pipeline_tables())   # giả lập pipeline đã chạy
    before = {t: [c["name"] for c in inspect(engine).get_columns(t)] for t in PIPELINE_TABLES}

    init_db(engine)

    names = set(inspect(engine).get_table_names())
    assert {t.name for t in _own_tables()} <= names
    after = {t: [c["name"] for c in inspect(engine).get_columns(t)] for t in PIPELINE_TABLES}
    assert after == before                                         # bảng của pipeline không bị đụng tới


def test_init_db_upgrades_legacy_metric_results(engine):
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE metric_results DROP CONSTRAINT uq_metric_result_term_revision"))
        conn.execute(text("ALTER TABLE metric_results DROP COLUMN revision"))
        conn.execute(text("ALTER TABLE metric_results DROP COLUMN source_hash"))
        conn.execute(text("ALTER TABLE metric_results ADD CONSTRAINT uq_metric_result_term "
                          "UNIQUE (metric_definition_id, learner_id, academic_year, semester)"))
    init_db(engine)
    init_db(engine)  # khởi động lại không gây xung đột migration
    columns = {c["name"] for c in inspect(engine).get_columns("metric_results")}
    assert {"revision", "source_hash"} <= columns
    constraints = {c["name"] for c in inspect(engine).get_unique_constraints("metric_results")}
    assert "uq_metric_result_term_revision" in constraints
    assert "uq_metric_result_term" not in constraints
