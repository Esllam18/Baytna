from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.db_models import UserEntity


def test_database_state_survives_across_requests(client):
    sent = client.post("/api/v1/auth/send-otp", json={"phone": "01022223333"})
    otp = sent.json()["development_otp"]

    verified = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone": "01022223333", "code": otp},
    )
    assert verified.status_code == 200

    with SessionLocal() as db:
        stored = db.scalar(
            select(UserEntity).where(UserEntity.phone == "+201022223333")
        )
        assert stored is not None
        user_id = stored.id

    me = client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {verified.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["id"] == str(user_id)
