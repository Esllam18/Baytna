def test_release_health_endpoint_is_safe_and_versioned(client):
    response = client.get("/health/release")
    assert response.status_code == 200

    body = response.json()
    assert body["service"] == "baytna-api"
    assert body["version"] == "0.50.0"
    assert body["environment"] == "development"
    assert body["slot"] == "local"
    assert body["migration_head"] == "0025_sprint50"

    serialized = response.text.lower()
    assert "jwt_secret" not in serialized
    assert "password" not in serialized
    assert "paymob_secret" not in serialized
    assert "twilio_auth" not in serialized


def test_root_identifies_sprint42_launch_hardening(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["sprint"] == "50"
    assert response.json()["status"] == "launch-day-slo-post-launch-stabilization"
