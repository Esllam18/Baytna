def test_customer_home_matches_sprint34_frontend_shape(login):
    response = login["client"].get(
        "/api/v1/customer/home",
        headers=login["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) >= {"customer", "area", "featured_chefs", "today"}
    assert "chefs" not in body
    assert "today_items" not in body
    assert isinstance(body["featured_chefs"], list)
    assert set(body["today"]) >= {"title", "service_date", "items"}


def test_public_chefs_match_sprint34_card_contract(client):
    response = client.get("/api/v1/chefs")
    assert response.status_code == 200
    chefs = response.json()
    assert chefs
    assert set(chefs[0]) >= {
        "id",
        "display_name",
        "specialty",
        "area",
        "rating",
        "is_verified",
        "is_open_today",
    }


def test_signature_menu_matches_dish_detail_contract(client):
    chefs = client.get("/api/v1/chefs").json()
    chef_id = chefs[0]["id"]
    response = client.get(f"/api/v1/chefs/{chef_id}/signature-menu")
    assert response.status_code == 200
    dishes = response.json()
    assert dishes
    assert set(dishes[0]) >= {
        "id",
        "chef_id",
        "name",
        "description",
        "category",
        "base_price_minor",
        "prep_notice_hours",
        "is_special_order_available",
        "image_url",
    }


def test_today_menu_contract_is_stable_for_sprint34(client):
    chefs = client.get("/api/v1/chefs").json()
    chef_id = chefs[0]["id"]
    response = client.get(f"/api/v1/chefs/{chef_id}/today-menu")
    assert response.status_code == 200
    body = response.json()
    assert set(body) >= {
        "chef_id",
        "service_date",
        "kitchen_status",
        "items",
    }
    assert isinstance(body["items"], list)
