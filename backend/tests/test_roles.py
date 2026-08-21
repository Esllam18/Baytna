def test_customer_cannot_open_admin_endpoint(login):
    response = login["client"].get(
        "/api/v1/admin/ping",
        headers=login["headers"],
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
