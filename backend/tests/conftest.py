import os

os.environ["BAYTNA_ENV"] = "development"
os.environ["BAYTNA_DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["BAYTNA_SEED_DEMO_DATA"] = "true"
os.environ["BAYTNA_DEV_RETURN_OTP"] = "true"
os.environ["BAYTNA_JWT_SECRET"] = "test-jwt-secret-that-is-longer-than-32-characters"
os.environ["BAYTNA_OTP_PEPPER"] = "test-otp-pepper"
os.environ["BAYTNA_REFRESH_TOKEN_PEPPER"] = "test-refresh-pepper"

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def login(client):
    sent = client.post("/api/v1/auth/send-otp", json={"phone": "01000000000"})
    assert sent.status_code == 200
    otp = sent.json()["development_otp"]

    verified = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone": "01000000000", "code": otp},
    )
    assert verified.status_code == 200
    body = verified.json()

    return {
        "client": client,
        "access_token": body["access_token"],
        "refresh_token": body["refresh_token"],
        "headers": {"Authorization": f"Bearer {body['access_token']}"},
        "body": body,
    }
