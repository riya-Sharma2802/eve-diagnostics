import os

# Must be set before the app is imported.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-at-least-32-bytes"
os.environ["WEBHOOK_SECRET"] = "test-webhook-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.models import User  # noqa: E402
from tests.helpers import future_iso  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    return TestClient(app)


def signup_and_login(client, email="user@example.com", password="Passw0rd!"):
    client.post(
        "/auth/signup",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    r = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def user_headers(client):
    return signup_and_login(client, "user@example.com")


@pytest.fixture
def other_headers(client):
    return signup_and_login(client, "other@example.com")


@pytest.fixture
def admin_headers(client):
    headers = signup_and_login(client, "admin@example.com")
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == "admin@example.com"))
        admin.is_admin = True
        db.commit()
    return headers


@pytest.fixture
def catalog(client, admin_headers):
    centre = client.post(
        "/centres/", headers=admin_headers, json={"name": "City Lab", "location": "Bengaluru"}
    ).json()
    test = client.post(
        "/tests/", headers=admin_headers, json={"name": "Lipid Profile"}
    ).json()
    r = client.post(
        f"/centres/{centre['id']}/tests",
        headers=admin_headers,
        json={"test_id": test["id"], "price": "1500.00"},
    )
    assert r.status_code == 201
    return {"centre_id": centre["id"], "test_id": test["id"], "price": "1500.00"}


@pytest.fixture
def booking(client, user_headers, catalog):
    r = client.post(
        "/bookings/",
        headers=user_headers,
        json={
            "centre_id": catalog["centre_id"],
            "test_id": catalog["test_id"],
            "appointment_time": future_iso(),
        },
    )
    assert r.status_code == 201
    return r.json()
