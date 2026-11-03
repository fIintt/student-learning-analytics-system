from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db.session import get_db
from app.main import create_app


def test_liveness_does_not_need_database():
    client = TestClient(create_app(create_tables=False))
    assert client.get("/api/v1/health/live").json() == {"status": "ok"}


def test_readiness_503_when_database_unreachable():
    class _DeadSession:
        def execute(self, *_args, **_kwargs):
            raise OperationalError("SELECT 1", {}, Exception("down"))

    app = create_app(create_tables=False)
    app.dependency_overrides[get_db] = lambda: _DeadSession()
    res = TestClient(app).get("/api/v1/health/ready")
    assert res.status_code == 503
    assert res.json() == {"status": "not_ready"}


def test_readiness_ready_with_all_tables(engine, app):
    res = TestClient(app).get("/api/v1/health/ready")
    assert res.status_code == 200
    assert res.json() == {"status": "ready"}
