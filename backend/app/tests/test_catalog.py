from app.models import AcademicStatus, LearnerGroup, Program, Student
from app.services import group_service


def _extra_program(db, program_id="P2"):
    db.add(Program(program_id=program_id, program_name_vi="Chương trình 2", program_name_en="Program 2",
                   major_code="7340201", program_type="EP", first_cohort_year=2020, last_cohort_year=2026))
    db.flush()


# --- GET /groups -------------------------------------------------------------------------

def test_groups_scoped_and_counted(client, world, auth):
    admin = client.get("/api/v1/groups", headers=auth["admin"]).json()
    assert [(g["name"], g["learner_count"]) for g in admin["items"]] == [("P1-2022", 2), ("P1-2023", 2)]
    assert admin["items"][0] == {"id": world["group_a"].id, "name": "P1-2022", "program_id": "P1",
                                 "program_name": "Chương trình 1", "cohort": 2022, "learner_count": 2}

    for role in ("reviewer",):
        body = client.get("/api/v1/groups", headers=auth[role]).json()
        assert [g["name"] for g in body["items"]] == ["P1-2022"] and body["total"] == 1


def test_catalog_requires_login(client, world):
    for url in ("/api/v1/groups", "/api/v1/learners", "/api/v1/programs"):
        assert client.get(url).status_code == 401


# --- GET /learners -------------------------------------------------------------------------

def test_learners_scoped_to_viewer_groups(client, world, auth):
    admin = client.get("/api/v1/learners", headers=auth["admin"]).json()
    assert admin["total"] == 4
    viewer = client.get("/api/v1/learners", headers=auth["reviewer"]).json()
    assert [l["id"] for l in viewer["items"]] == ["HS001", "HS002"]
    assert viewer["items"][0] == {"id": "HS001", "full_name": "Học sinh 1", "program_id": "P1",
                                  "program_name": "Chương trình 1", "cohort": 2022, "academic_status": "studying"}


def test_learners_filters(client, world, auth):
    admin = auth["admin"]
    by_group = client.get("/api/v1/learners", params={"group_id": world["group_b"].id}, headers=admin).json()
    assert [l["id"] for l in by_group["items"]] == ["HS003", "HS004"]
    assert client.get("/api/v1/learners", params={"cohort": 2022}, headers=admin).json()["total"] == 2
    assert client.get("/api/v1/learners", params={"program_id": "KHAC"}, headers=admin).json()["total"] == 0

    def ids(q):
        res = client.get("/api/v1/learners", params={"q": q}, headers=admin).json()
        return [l["id"] for l in res["items"]]

    assert ids("SINH 3") == ["HS003"]          # tìm theo tên, không phân biệt hoa thường
    assert ids("HS00") == ["HS001", "HS002", "HS003", "HS004"]   # tìm theo đầu mã
    assert ids("%") == []                      # ký tự đặc biệt không bị hiểu là ký tự đại diện


def test_learners_group_outside_scope(client, world, auth):
    res = client.get("/api/v1/learners", params={"group_id": world["group_b"].id}, headers=auth["reviewer"])
    assert res.status_code == 403
    assert client.get("/api/v1/learners", params={"group_id": 999}, headers=auth["admin"]).status_code == 404


# --- GET /programs ---------------------------------------------------------------------------

def test_programs_scoped(client, db, world, auth):
    _extra_program(db)
    db.add(Student(student_id="HS100", name="Học sinh 100", program_id="P2", cohort=2022,
                   academic_status=AcademicStatus.STUDYING))
    db.commit()

    admin = client.get("/api/v1/programs", headers=auth["admin"]).json()
    assert [p["id"] for p in admin["items"]] == ["P1", "P2"]
    assert admin["items"][0] == {"id": "P1", "name": "Chương trình 1", "name_en": "Program 1",
                                 "program_type": "Standard", "first_cohort_year": 2020, "last_cohort_year": 2026}
    viewer = client.get("/api/v1/programs", headers=auth["reviewer"]).json()
    assert [p["id"] for p in viewer["items"]] == ["P1"]       # P2 không có sinh viên trong phạm vi


# --- đồng bộ nhóm từ bảng students ------------------------------------------------------------

def test_sync_groups_adds_only_missing_groups(db, world):
    assert group_service.sync_groups(db) == 0                  # world đã có đủ nhóm

    _extra_program(db)
    db.add_all([Student(student_id="HS200", name="Mới 1", program_id="P2", cohort=2024,
                        academic_status=AcademicStatus.STUDYING),
                Student(student_id="HS201", name="Mới 2", program_id="P2", cohort=2024,
                        academic_status=AcademicStatus.STUDYING),
                Student(student_id="HS202", name="Mới 3", program_id="P1", cohort=2024,
                        academic_status=AcademicStatus.STUDYING)])
    db.commit()
    assert group_service.sync_groups(db) == 2
    assert group_service.sync_groups(db) == 0

    names = sorted(g.name for g in db.query(LearnerGroup).all())
    assert names == ["P1-2022", "P1-2023", "P1-2024", "P2-2024"]
    new = db.query(LearnerGroup).filter_by(name="P2-2024").one()
    assert new.description == "Chương trình 2 - Khoá 2024"
    # nhóm cũ giữ nguyên, người dùng được gán nhóm cũ không bị ảnh hưởng
    assert [g.name for g in world["viewer"].groups] == ["P1-2022"]
