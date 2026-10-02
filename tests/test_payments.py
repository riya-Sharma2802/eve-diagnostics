def _pay(client, headers, booking_id, outcome=None):
    body = {"booking_id": booking_id}
    if outcome:
        body["simulate_outcome"] = outcome
    return client.post("/payments/", headers=headers, json=body)


def test_successful_payment_confirms_booking(client, booking, user_headers):
    r = _pay(client, user_headers, booking["id"], "SUCCESS")
    assert r.status_code == 201
    assert r.json()["payment"]["status"] == "SUCCESS"
    assert r.json()["booking"]["status"] == "CONFIRMED"
    got = client.get(f"/bookings/{booking['id']}", headers=user_headers).json()
    assert got["status"] == "CONFIRMED"


def test_failed_payment_marks_booking_failed_then_retry_succeeds(client, booking, user_headers):
    r = _pay(client, user_headers, booking["id"], "FAILED")
    assert r.json()["booking"]["status"] == "FAILED"

    r = _pay(client, user_headers, booking["id"], "SUCCESS")
    assert r.status_code == 201
    assert r.json()["booking"]["status"] == "CONFIRMED"


def test_random_outcome_is_one_of_two(client, booking, user_headers):
    r = _pay(client, user_headers, booking["id"])
    assert r.json()["payment"]["status"] in ("SUCCESS", "FAILED")


def test_cannot_pay_twice(client, booking, user_headers):
    _pay(client, user_headers, booking["id"], "SUCCESS")
    assert _pay(client, user_headers, booking["id"], "SUCCESS").status_code == 409


def test_cannot_pay_for_cancelled_booking(client, booking, user_headers):
    client.post(f"/bookings/{booking['id']}/cancel", headers=user_headers)
    assert _pay(client, user_headers, booking["id"], "SUCCESS").status_code == 409


def test_invalid_or_foreign_booking(client, booking, user_headers, other_headers):
    assert _pay(client, user_headers, 9999).status_code == 404
    assert _pay(client, other_headers, booking["id"]).status_code == 404
    assert client.post("/payments/", headers=user_headers, json={}).status_code == 422


def test_payment_requires_auth(client, booking):
    assert client.post("/payments/", json={"booking_id": booking["id"]}).status_code == 401
