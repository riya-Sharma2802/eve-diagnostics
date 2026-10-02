import json

from fastapi import APIRouter, Depends
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import UnprocessableError
from app.deps import get_current_user, verified_webhook_body
from app.models.models import User
from app.schemas.booking import BookingOut
from app.schemas.payment import (
    PaymentCreate,
    PaymentOut,
    PaymentResult,
    WebhookPayload,
    WebhookResult,
)
from app.services import payment_service as svc

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/", response_model=PaymentResult, status_code=201)
def make_payment(
    payload: PaymentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mock payment: randomly SUCCESS/FAILED (or forced via simulate_outcome)."""
    payment, booking = svc.create_payment(
        db, user, payload.booking_id, payload.simulate_outcome
    )
    return PaymentResult(
        payment=PaymentOut.model_validate(payment),
        booking=BookingOut.model_validate(booking),
    )


@router.post("/webhook/", response_model=WebhookResult)
def payment_webhook(
    raw: bytes = Depends(verified_webhook_body),
    db: Session = Depends(get_db),
):
    """Idempotent provider webhook. Requires a valid X-Webhook-Signature header."""
    try:
        event = WebhookPayload.model_validate_json(raw)
    except ValidationError as exc:
        raise UnprocessableError(
            json.loads(exc.json(include_url=False, include_input=False))
        )
    return svc.process_webhook(db, event, json.loads(raw))
