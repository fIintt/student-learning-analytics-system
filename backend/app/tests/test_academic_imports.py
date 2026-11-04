from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess

import pytest
from sqlalchemy import select, text

from app.core.config import settings
from app.models import AcademicImport, AcademicPerformance, Role, User
from app.services import academic_import_service as service
from app.tests.conftest import add_term, login

URL = "/api/v1/academic-imports"
HEADER = "student_id,academic_year,semester,registered_credits,passed_credits,failed_credits,semester_gpa,cumulative_gpa\n"


@pytest.fixture(autouse=True)
def import_storage(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "academic_import_dir", tmp_path / "uploads")


def upload(client, auth, rows, role="reviewer", filename="grades.csv"):
    response = client.post(URL, headers=auth[role], files={"file": (filename, (HEADER + rows).encode("utf-8"), "text/csv")})
    assert response.status_code == 202, response.text
    job_id = response.json()["id"]
    detail = client.get(f"{URL}/{job_id}", headers=auth[role])
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == "ready", detail.text
    return job_id, detail.json()


def confirm(client, auth, job_id, role="reviewer"):
    response = client.post(f"{URL}/{job_id}/confirm", headers=auth[role])
    assert response.status_code == 202, response.text
    detail = client.get(f"{URL}/{job_id}", headers=auth[role])
    assert detail.json()["status"] == "completed", detail.text
    return detail.json()


def test_upload_preview_then_append_only_and_idempotence(client, db, world, auth):
    add_term(db, "HS001", "2025-2026", 1, cumulative_gpa=1.5)
    rows = ("HS001,2026/2027,1,20,18,2,3.10,2.85\n"
            "HS001,2026/2027,1,20,18,2,3.10,2.85\n"
            "HS001,2025-2026,1,18,18,0,3.0,1.5\n"
            "HS001,2025-2026,2,18,18,0,3.0,2.7\n")
    job_id, preview = upload(client, auth, rows)
    assert (preview["total_rows"], preview["duplicated_rows"], preview["new_rows"], preview["unchanged_rows"]) == (4, 1, 2, 1)
    assert len(preview["preview_rows"]) == 2
    assert db.query(AcademicPerformance).count() == 1  # preview never inserts grades
    result = confirm(client, auth, job_id)
    assert result["inserted_rows"] == 2
    assert db.query(AcademicPerformance).count() == 3
    db.expire_all()
    assert db.get(AcademicPerformance, ("HS001", "2025-2026", 1)).cumulative_gpa == 1.5
    assert confirm(client, auth, job_id)["inserted_rows"] == 2
    again, _ = upload(client, auth, rows)
    assert confirm(client, auth, again)["inserted_rows"] == 0
    assert db.query(AcademicPerformance).count() == 3


@pytest.mark.parametrize("role", ["reviewer", "admin"])
def test_conflicting_grade_rejected_even_for_admin(client, db, world, auth, role):
    add_term(db, "HS001", cumulative_gpa=1.5)
    rows = "HS001,2025-2026,1,18,18,0,3,2.8\nHS001,2026-2027,1,20,20,0,3,3\n"
    job_id, preview = upload(client, auth, rows, role)
    assert preview["rejected_rows"] == 1 and preview["new_rows"] == 1
    errors = client.get(f"{URL}/{job_id}/errors?size=1", headers=auth[role]).json()
    assert errors["items"][0]["reason"] == "existing_record_conflict"
    assert errors["items"][0]["row_number"] == 2
    result = confirm(client, auth, job_id, role)
    assert result["inserted_rows"] == 1
    db.expire_all()
    assert db.get(AcademicPerformance, ("HS001", "2025-2026", 1)).cumulative_gpa == 1.5


def test_invalid_outside_scope_unknown_and_conflicting_duplicates(client, db, world, auth):
    rows = ("HS001,2026-2027,1,20,20,0,5,2\n"  # invalid GPA
            "HS003,2026-2027,1,20,20,0,3,3\n"  # outside scope
            "UNKNOWN,2026-2027,1,20,20,0,3,3\n"
            "HS001,2026-2027,2,20,20,0,3,3\n"
            "HS001,2026-2027,2,20,20,0,2,2\n")
    job_id, preview = upload(client, auth, rows)
    assert preview["rejected_rows"] == 5 and preview["new_rows"] == 0
    reasons = [r["reason"] for r in client.get(f"{URL}/{job_id}/errors", headers=auth["reviewer"]).json()["items"]]
    assert "learner_outside_scope" in reasons
    assert any("unknown_student_id" in r for r in reasons)
    assert any("semester_gpa_out_of_range" in r for r in reasons)
    assert reasons.count("duplicate_key") == 2
    assert confirm(client, auth, job_id)["inserted_rows"] == 0
    assert db.query(AcademicPerformance).count() == 0


def test_permissions_are_rechecked_on_confirmation(client, db, world, auth):
    job_id, _ = upload(client, auth, "HS001,2026-2027,1,20,20,0,3,3\n")
    world["reviewer"].groups = []
    db.commit()
    result = confirm(client, auth, job_id)
    assert result["rejected_rows"] == 1 and result["inserted_rows"] == 0
    assert db.query(AcademicPerformance).count() == 0


def test_history_errors_and_confirm_are_owner_or_admin_only(client, db, world, auth):
    job_id, _ = upload(client, auth, "HS001,2026-2027,1,20,20,0,3,3\n")
    other = User(email="other@test.local", full_name="Other", role=Role.REVIEWER,
                 hashed_password=world["reviewer"].hashed_password, is_active=True, groups=[world["group_a"]])
    db.add(other)
    db.commit()
    other_auth = login(client, other.email)
    assert client.get(URL, headers=other_auth).json()["total"] == 0
    for suffix, method in (("", "get"), ("/errors", "get"), ("/confirm", "post")):
        assert client.request(method, f"{URL}/{job_id}{suffix}", headers=other_auth).status_code == 403
    assert client.get(URL, headers=auth["admin"]).json()["total"] == 1
    assert client.get(f"{URL}/{job_id}", headers=auth["admin"]).status_code == 200
    assert client.get(f"{URL}/{job_id}", headers=auth["viewer"]).status_code == 403
    assert client.get(f"{URL}/{job_id}").status_code == 401
    assert client.get(URL + "/999", headers=auth["admin"]).status_code == 404


@pytest.mark.parametrize("different", [False, True])
def test_concurrent_imports_never_overwrite(client, db, world, auth, different):
    first, _ = upload(client, auth, "HS001,2026-2027,1,20,20,0,3,3\n")
    second, _ = upload(client, auth, f"HS001,2026-2027,1,20,20,0,3,{2 if different else 3}\n")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda job: confirm(client, auth, job), [first, second]))
    assert sum(r["inserted_rows"] for r in results) == 1
    assert sum(r["rejected_rows"] for r in results) == int(different)
    assert db.query(AcademicPerformance).count() == 1


def test_csv_validation_template_limits_and_safe_filename(client, db, world, auth, monkeypatch):
    template = client.get(URL + "/template", headers=auth["reviewer"])
    assert template.status_code == 200 and b"registered_credits" in template.content
    assert client.get(URL + "/template", headers=auth["viewer"]).status_code == 403
    assert client.post(URL, headers=auth["viewer"], files={"file": ("a.csv", b"x")}).status_code == 403
    assert client.post(URL, headers=auth["admin"], files={"file": ("a.exe", b"x")}).status_code == 400
    assert client.post(URL, headers=auth["admin"], files={"file": ("a.csv", b"")}).status_code == 400
    monkeypatch.setattr(settings, "academic_import_max_bytes", 10)
    assert client.post(URL, headers=auth["admin"], files={"file": ("a.csv", b"x" * 11)}).status_code == 413
    monkeypatch.setattr(settings, "academic_import_max_bytes", 10485760)
    response = client.post(URL, headers=auth["reviewer"], files={"file": ("grades.csv", b"student_id,semester_gpa\nHS001,3\n")})
    failed = client.get(f"{URL}/{response.json()['id']}", headers=auth["reviewer"]).json()
    assert failed["status"] == "failed" and "cột" in failed["error_message"]
    assert client.post(f"{URL}/{failed['id']}/confirm", headers=auth["reviewer"]).status_code == 409
    job_id, _ = upload(client, auth, "HS001,2026-2027,1,20,20,0,3,3\n", filename="../../grades.csv")
    job = db.get(AcademicImport, job_id)
    assert job.filename == "grades.csv"
    assert service._file_path(job.storage_key).is_file()


def test_worker_failure_and_stale_job_do_not_write_grades(client, db, world, auth, monkeypatch):
    monkeypatch.setattr(settings, "academic_import_max_rows", 1)
    response = client.post(URL, headers=auth["reviewer"], files={"file": ("x.csv", (HEADER +
        "HS001,2026-2027,1,20,20,0,3,3\nHS002,2026-2027,1,20,20,0,3,3\n").encode())})
    assert client.get(f"{URL}/{response.json()['id']}", headers=auth["reviewer"]).json()["status"] == "failed"
    monkeypatch.setattr(settings, "academic_import_max_rows", 50000)
    job_id, _ = upload(client, auth, "HS001,2026-2027,1,20,20,0,3,3\n")
    job = db.get(AcademicImport, job_id)
    db.refresh(job)
    job.status = "processing"
    job.updated_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
    db.commit()
    assert client.get(f"{URL}/{job_id}", headers=auth["reviewer"]).json()["status"] == "failed"
    assert db.query(AcademicPerformance).count() == 0


def test_cli_ingestion_rejects_old_grade_changes(engine, db, world, tmp_path):
    add_term(db, "HS001", cumulative_gpa=1.5)
    path = tmp_path / "grades.csv"
    path.write_text(HEADER + "HS001,2025-2026,1,18,18,0,3,2.8\nHS001,2026-2027,1,20,20,0,3,3\n", encoding="utf-8")
    schema = db.scalar(text("SELECT current_schema()"))
    context = {"dsn": engine.url.set(drivername="postgresql").render_as_string(hide_password=False),
               "schema": schema, "path": str(path), "output": str(tmp_path)}
    code = '''import json,sys
from pathlib import Path
import psycopg
from psycopg import sql
import pipeline.pipelines.academic_performance as module
c=json.load(sys.stdin)
module.REJECTED_ACADEMIC_PERFORMANCE_PATH=Path(c["output"])/"rejected"
module.PROCESSED_ACADEMIC_PERFORMANCE_PATH=Path(c["output"])/"processed"
with psycopg.connect(c["dsn"]) as conn:
    conn.execute("SELECT set_config('search_path',%s,false)",(sql.Identifier(c["schema"]).as_string(conn),))
    results=[]
    for _ in range(2):
        results.append(module.run_academic_performance_pipeline(conn,Path(c["path"])))
        conn.commit()
    print(json.dumps(results))
'''
    command, root = service._command()
    result = subprocess.run([command[0], "-c", code], input=json.dumps(context), text=True, encoding="utf-8",
                            env={**os.environ, "PYTHONPATH": str(root / "src")}, capture_output=True, check=True)
    first, second = json.loads(result.stdout)
    assert first["rejected"] == 1 and first["loaded"] == 1
    assert second["rejected"] == 1 and second["loaded"] == 0
    db.expire_all()
    assert db.get(AcademicPerformance, ("HS001", "2025-2026", 1)).cumulative_gpa == 1.5


def test_database_failure_rolls_back_whole_confirmation(client, db, world, auth):
    job_id, _ = upload(client, auth, "HS001,2026-2027,1,20,20,0,3,3\nHS002,2026-2027,1,20,20,0,3,3\n")
    db.execute(text("ALTER TABLE academic_performance ADD CONSTRAINT test_reject_second_student CHECK (student_id <> 'HS002')"))
    db.commit()
    response = client.post(f"{URL}/{job_id}/confirm", headers=auth["reviewer"])
    assert response.status_code == 202
    result = client.get(f"{URL}/{job_id}", headers=auth["reviewer"]).json()
    assert result["status"] == "failed" and result["inserted_rows"] == 0
    assert db.query(AcademicPerformance).count() == 0


def test_upload_against_actual_pipeline_sql_schema(empty_engine):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session
    from app.core.security import hash_password
    from app.db.session import Base, get_db
    from app.main import create_app

    with empty_engine.begin() as connection:
        for schema in sorted((settings.pipeline_dir / "sql/schemas").glob("*.sql")):
            connection.exec_driver_sql(schema.read_text(encoding="utf-8"))
        connection.exec_driver_sql("""INSERT INTO programs VALUES ('P1','Chương trình','Program','7340101','Standard',2020,2026)""")
        connection.exec_driver_sql("""INSERT INTO students VALUES ('11220001','Sinh viên','P1',2022,'studying')""")
    own_tables = [table for table in Base.metadata.sorted_tables if not table.info.get("pipeline")]
    Base.metadata.create_all(empty_engine, tables=own_tables)
    with Session(empty_engine) as session:
        session.add(User(email="admin@integration.local", full_name="Admin", role=Role.ADMIN,
                         hashed_password=hash_password("Test@123"), is_active=True))
        session.commit()

    app = create_app(create_tables=False)
    def test_db():
        with Session(empty_engine, expire_on_commit=False) as session:
            yield session
    app.dependency_overrides[get_db] = test_db
    with TestClient(app) as client:
        headers = {"admin": login(client, "admin@integration.local")}
        job_id, _ = upload(client, headers, "11220001,2026-2027,1,20,18,2,3.10,2.85\n", role="admin")
        assert confirm(client, headers, job_id, "admin")["inserted_rows"] == 1
    with Session(empty_engine) as session:
        grade = session.get(AcademicPerformance, ("11220001", "2026-2027", 1))
        assert grade.cumulative_gpa == 2.85 and grade.failed_credits == 2
