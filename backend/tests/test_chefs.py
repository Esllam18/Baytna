def test_list_chefs_is_database_backed(client):
    response = client.get("/api/v1/chefs")
    assert response.status_code == 200
    chefs = response.json()
    assert len(chefs) == 3
    assert chefs[0]["rating"] >= chefs[1]["rating"]


def test_filter_open_chefs(client):
    response = client.get(
        "/api/v1/chefs",
        params={"open_today": "true", "area": "6 أكتوبر"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert all(x["is_open_today"] for x in response.json())


def test_customer_home_requires_auth(client):
    response = client.get("/api/v1/customer/home")
    assert response.status_code == 401


def test_customer_home_uses_database(login):
    response = login["client"].get(
        "/api/v1/customer/home",
        headers=login["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["area"] == "6 أكتوبر"
    assert len(body["featured_chefs"]) == 2
