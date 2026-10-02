def test_public_listing_with_prices(client, catalog):
    r = client.get("/centres/")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    centre = body["items"][0]
    assert centre["name"] == "City Lab"
    assert centre["tests"][0]["name"] == "Lipid Profile"
    assert float(centre["tests"][0]["price"]) == 1500.0


def test_location_filter_and_pagination(client, admin_headers):
    for i in range(3):
        client.post("/centres/", headers=admin_headers, json={"name": f"C{i}", "location": "Mysuru"})
    client.post("/centres/", headers=admin_headers, json={"name": "X", "location": "Delhi"})

    r = client.get("/centres/", params={"location": "mysuru", "limit": 2})
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2


def test_only_admin_can_create(client, user_headers):
    r = client.post("/centres/", headers=user_headers, json={"name": "N", "location": "L"})
    assert r.status_code == 403
    assert client.post("/centres/", json={"name": "N", "location": "L"}).status_code == 401


def test_invalid_price_and_duplicates(client, admin_headers, catalog):
    url = f"/centres/{catalog['centre_id']}/tests"
    dup = client.post(url, headers=admin_headers, json={"test_id": catalog["test_id"], "price": "10"})
    assert dup.status_code == 409

    t = client.post("/tests/", headers=admin_headers, json={"name": "Another"}).json()
    assert client.post(url, headers=admin_headers, json={"test_id": t["id"], "price": "-5"}).status_code == 422
    assert client.post(url, headers=admin_headers, json={"test_id": 9999, "price": "5"}).status_code == 404


def test_unknown_centre_is_404(client):
    assert client.get("/centres/9999").status_code == 404
