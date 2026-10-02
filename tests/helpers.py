import json
from datetime import datetime, timedelta, timezone

from app.core.security import sign_payload


def future_iso(days: int = 2) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def past_iso() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()


def post_webhook(client, event: dict, signature: str | None = None):
    body = json.dumps(event).encode()
    sig = sign_payload(body) if signature is None else signature
    return client.post(
        "/payments/webhook/",
        content=body,
        headers={"X-Webhook-Signature": sig, "Content-Type": "application/json"},
    )
