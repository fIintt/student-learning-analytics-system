from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.schema import CreateSchema, DropSchema

from app.core.security import pwd_context
from app.core.config import settings
from app.db.session import Base, get_db, make_engine
from app.main import create_app
from app.models import AcademicPerformance, AcademicStatus, Alert, LearnerGroup, Program, Role, Student, User
from app.services import group_service

TEST_PASSWORD = "Test@123"
# Băm một lần, số vòng bcrypt tối thiểu để test chạy nhanh (app thật vẫn dùng mặc định).
_TEST_PASSWORD_HASH = pwd_context.hash(TEST_PASSWORD, rounds=4)


@pytest.fixture()
def empty_engine():
    """Mỗi test có schema PostgreSQL riêng, không truy cập schema ứng dụng."""
    schema = "test_" + uuid4().hex
    admin_engine = make_engine(settings.test_database_url or settings.effective_database_url)
    with admin_engine.begin() as conn:
        conn.execute(CreateSchema(schema))
    eng = make_engine(
        admin_engine.url.render_as_string(hide_password=False),
        connect_args={"options": f"-csearch_path={schema} -ctimezone=UTC"},
    )
    try:
        yield eng
    finally:
        eng.dispose()
        try:
            with admin_engine.begin() as conn:
                conn.execute(DropSchema(schema, cascade=True))
        finally:
            admin_engine.dispose()


@pytest.fixture()
def engine(empty_engine):
    import app.models  # noqa: F401

    Base.metadata.create_all(empty_engine)  # dựng cả bảng nguồn cho dữ liệu test
    return empty_engine


@pytest.fixture()
def db(engine) -> Session:
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    yield session
    session.close()


@pytest.fixture()
def app(engine):
    test_app = create_app(create_tables=False)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _get_db():
        s = TestingSession()
        try:
            yield s
        finally:
            s.close()

    test_app.dependency_overrides[get_db] = _get_db
    return test_app


@pytest.fixture()
def client(app) -> TestClient:
    return TestClient(app)


@pytest.fixture()
def world(db):
    """Chương trình P1; nhóm A (P1-2022: HS001, HS002) và nhóm B (P1-2023: HS003, HS004), mọi SV đang học.

    Tài khoản: admin (mọi nhóm), reviewer và viewer (chỉ nhóm A).
    """
    program = Program(program_id="P1", program_name_vi="Chương trình 1", program_name_en="Program 1",
                      major_code="7340101", program_type="Standard", first_cohort_year=2020, last_cohort_year=2026)
    db.add(program)
    db.flush()
    learners = [Student(student_id=f"HS{i:03d}", name=f"Học sinh {i}", program_id="P1",
                        cohort=2022 if i <= 2 else 2023, academic_status=AcademicStatus.STUDYING)
                for i in range(1, 5)]
    db.add_all(learners)
    db.commit()
    group_service.sync_groups(db)
    groups = {g.cohort: g for g in db.query(LearnerGroup).all()}
    group_a, group_b = groups[2022], groups[2023]

    def mk(email, role, group_list=()):
        return User(email=email, full_name=email.split("@")[0], role=role,
                    hashed_password=_TEST_PASSWORD_HASH, is_active=True, groups=list(group_list))

    admin = mk("admin@test.local", Role.ADMIN)
    reviewer = mk("reviewer@test.local", Role.REVIEWER, [group_a])
    viewer = mk("viewer@test.local", Role.VIEWER, [group_a])
    viewer.student_id = "HS001"
    db.add_all([admin, reviewer, viewer])
    db.commit()
    return {
        "program": program, "group_a": group_a, "group_b": group_b, "learners": learners,
        "admin": admin, "reviewer": reviewer, "viewer": viewer,
    }


def login(client: TestClient, email: str, password: str = TEST_PASSWORD) -> dict:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture()
def auth(client, world):
    return {role: login(client, world[role].email) for role in ("admin", "reviewer", "viewer")}


def add_term(db, student_id: str, year: str = "2025-2026", semester: int = 1, registered: int = 18,
             failed: int = 0, semester_gpa: float = 3.0, cumulative_gpa: float = 3.0) -> None:
    """Thêm một dòng kết quả học kỳ vào bảng academic_performance (như pipeline đã nạp)."""
    db.add(AcademicPerformance(student_id=student_id, academic_year=year, semester=semester,
                               registered_credits=registered, passed_credits=registered - failed,
                               failed_credits=failed, semester_gpa=semester_gpa, cumulative_gpa=cumulative_gpa))
    db.commit()


def make_definition(db, user, *, code="CUM_GPA", status=None, formula_type="cumulative_gpa",
                    formula_params=None, threshold=None, version=1, purpose="Hỗ trợ sinh viên có GPA thấp"):
    from app.models import MetricDefinition, MetricStatus

    definition = MetricDefinition(
        code=code, version=version, name=code, purpose=purpose, formula_type=formula_type,
        formula_params=formula_params if formula_params is not None else {},
        threshold=threshold or {"operator": "<", "value": 2.0},
        status=status or MetricStatus.APPROVED, created_by=user.id,
    )
    db.add(definition)
    db.commit()
    return definition


@pytest.fixture()
def alerts(client, db, world, auth):
    """Mỗi sinh viên có 1 cảnh báo pending_review (HS001, HS002 thuộc nhóm A; HS003, HS004 nhóm B)."""
    for learner in world["learners"]:
        add_term(db, learner.student_id, cumulative_gpa=1.5)
    definition = make_definition(db, world["admin"])  # GPA tích luỹ 1.5 < 2.0 → mọi người đều bị cảnh báo
    res = client.post("/api/v1/metrics/compute", json={"metric_definition_id": definition.id}, headers=auth["admin"])
    assert res.json()["alerts_created"] == 4
    by_learner = {a.learner_id: a for a in db.query(Alert).all()}
    return [by_learner[l.student_id] for l in world["learners"]]
