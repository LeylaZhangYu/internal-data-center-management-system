import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import Base, get_db  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.models import Area, DataCenter, Rack, RackOrientationEnum, RoleEnum, User  # noqa: E402


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    admin = User(username="admin", full_name="Admin", hashed_password=get_password_hash("admin123"), role=RoleEnum.admin)
    db.add(admin)
    db.flush()
    dc = DataCenter(name="测试机房", location="上海", owner="IT")
    db.add(dc)
    db.flush()
    area = Area(data_center_id=dc.id, name="A区", row_count=2, column_count=2)
    db.add(area)
    db.flush()
    rack1 = Rack(data_center_id=dc.id, area_id=area.id, code="A01", total_u=42, orientation=RackOrientationEnum.north)
    rack2 = Rack(data_center_id=dc.id, area_id=area.id, code="A02", total_u=42, orientation=RackOrientationEnum.north)
    db.add_all([rack1, rack2])
    db.commit()
    db.close()
    yield


@pytest.fixture()
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def auth_headers(client: TestClient, username: str, password: str):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_headers(client):
    return auth_headers(client, "admin", "admin123")

