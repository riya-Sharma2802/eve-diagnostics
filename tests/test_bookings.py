from decimal import Decimal

from tests.helpers import future_iso, past_iso


def _payload(catalog, when=None):
    return {
        "centre_id": catalog["centre_id"],
        "test_id": catalog["test_id"],
        "appointment_time": when or future_iso(),
    }


def test_create_booking_snapshots_price(client, user_headers, catalog):
    r = client.post("/bookings/", headers=user_headers, json=_payload(catalog))
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "PENDING"
    assert Decimal(body["amount"]) == Decimal(catalog["price"])


def test_requires_auth(client, catalog):
    assert client.post("/bookings/", json=_payload(catalog)).status_code == 401


def test_past_time_rejected(client, user_headers, catalog):
    r = client.post("/bookings/", headers=user_headers, json=_payload(catalog, past_iso()))
    assert r.status_code == 422


def test_test_not_offered_at_centre(client, user_headers, admin_headers, catalog):
    other_test = client.post("/tests/", headers=admin_headers, json={"name": "MRI"}).json()
    payload = {**_payload(catalog), "test_id": other_test["id"]}
    assert client.post("/bookings/", headers=user_headers, json=payload).status_code == 404


def test_invalid_ids_and_body(client, user_headers):
    assert client.get("/bookings/9999", headers=user_headers).status_code == 404
    assert client.get("/bookings/abc", headers=user_headers).status_code == 422
    assert client.post("/bookings/", headers=user_headers, json={}).status_code == 422


def test_cannot_see_or_cancel_someone_elses_booking(client, booking, other_headers):
    assert client.get(f"/bookings/{booking['id']}", headers=other_headers).status_code == 404
    assert client.post(f"/bookings/{booking['id']}/cancel", headers=other_headers).status_code == 404
    assert client.get("/bookings/", headers=other_headers).json()["total"] == 0


def test_cancel_flow(client, booking, user_headers):
    r = client.post(f"/bookings/{booking['id']}/cancel", headers=user_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "CANCELLED"
    again = client.post(f"/bookings/{booking['id']}/cancel", headers=user_headers)
    assert again.status_code == 409


def test_list_is_paginated_and_filterable(client, user_headers, catalog):
    for _ in range(3):
        client.post("/bookings/", headers=user_headers, json=_payload(catalog))
    r = client.get("/bookings/", headers=user_headers, params={"limit": 2})
    assert r.json()["total"] == 3 and len(r.json()["items"]) == 2
    r = client.get("/bookings/", headers=user_headers, params={"status": "CONFIRMED"})
    assert r.json()["total"] == 0
