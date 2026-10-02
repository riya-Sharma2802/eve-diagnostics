from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models.models import Booking, Payment, WebhookEvent
from tests.helpers import post_webhook


def _failed_payment(client, user_headers, booking):
    r = client.post(
        "/payments/",
        headers=user_headers,
        json={"booking_id": booking["id"], "simulate_outcome": "FAILED"},
    )
    return r.json()["payment"]


def _count(model):
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(model))


def test_webhook_updates_booking(client, booking, user_headers):
    payment = _failed_payment(client, user_headers, booking)
    event = {
        "event_id": "evt_1",
        "provider_reference": payment["provider_reference"],
        "status": "SUCCESS",
    }
    r = post_webhook(client, event)
    assert r.status_code == 200
    assert r.json() == {"status": "processed", "booking_status": "CONFIRMED"}
    got = client.get(f"/bookings/{booking['id']}", headers=user_headers).json()
    assert got["status"] == "CONFIRMED"


def test_duplicate_event_is_idempotent(client, booking, user_headers):
    payment = _failed_payment(client, user_headers, booking)
    event = {
        "event_id": "evt_dup",
        "provider_reference": payment["provider_reference"],
        "status": "SUCCESS",
    }
    first = post_webhook(client, event)
    second = post_webhook(client, event)
    third = post_webhook(client, event)

    assert first.json()["status"] == "processed"
    assert second.status_code == third.status_code == 200
    assert second.json()["status"] == third.json()["status"] == "duplicate"

    # No duplicate payments / events, booking state unchanged.
    assert _count(Payment) == 1
    assert _count(WebhookEvent) == 1
    with SessionLocal() as db:
        assert db.scalar(select(Booking.status)).value == "CONFIRMED"


def test_replayed_old_event_does_not_undo_newer_state(client, booking, user_headers):
    payment = _failed_payment(client, user_headers, booking)
    ref = payment["provider_reference"]
    post_webhook(client, {"event_id": "e1", "provider_reference": ref, "status": "SUCCESS"})
    # Replaying e1 must be a no-op even after a different event arrived.
    post_webhook(client, {"event_id": "e2", "provider_reference": ref, "status": "SUCCESS"})
    again = post_webhook(client, {"event_id": "e1", "provider_reference": ref, "status": "FAILED"})
    assert again.json()["status"] == "duplicate"
    got = client.get(f"/bookings/{booking['id']}", headers=user_headers).json()
    assert got["status"] == "CONFIRMED"


def test_cancelled_booking_is_not_resurrected(client, booking, user_headers):
    # Pay successfully, then cancel (CONFIRMED bookings can be cancelled).
    r = client.post(
        "/payments/",
        headers=user_headers,
        json={"booking_id": booking["id"], "simulate_outcome": "SUCCESS"},
    )
    payment = r.json()["payment"]
    cancel = client.post(f"/bookings/{booking['id']}/cancel", headers=user_headers)
    assert cancel.status_code == 200

    # A late provider event must not bring the booking back.
    r = post_webhook(
        client,
        {"event_id": "e9", "provider_reference": payment["provider_reference"], "status": "SUCCESS"},
    )
    assert r.status_code == 200
    got = client.get(f"/bookings/{booking['id']}", headers=user_headers).json()
    assert got["status"] == "CANCELLED"


def test_bad_signature_rejected(client, booking, user_headers):
    payment = _failed_payment(client, user_headers, booking)
    event = {"event_id": "x", "provider_reference": payment["provider_reference"], "status": "SUCCESS"}
    assert post_webhook(client, event, signature="deadbeef").status_code == 401
    assert client.post("/payments/webhook/", json=event).status_code == 401
    assert _count(WebhookEvent) == 0


def test_unknown_reference_and_invalid_body(client):
    unknown = {"event_id": "u1", "provider_reference": "nope", "status": "SUCCESS"}
    assert post_webhook(client, unknown).status_code == 404
    assert _count(WebhookEvent) == 0

    bad_status = {"event_id": "u2", "provider_reference": "nope", "status": "MAYBE"}
    assert post_webhook(client, bad_status).status_code == 422
    assert post_webhook(client, {"event_id": "u3"}).status_code == 422
