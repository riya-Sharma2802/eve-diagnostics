import logging
import random
import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.models.models import (
    Booking,
    BookingStatus,
    Payment,
    PaymentStatus,
    User,
    WebhookEvent,
)
from app.schemas.payment import WebhookPayload, WebhookResult

logger = logging.getLogger(__name__)


def _roll_outcome() -> PaymentStatus:
    if random.random() < settings.mock_payment_success_rate:
        return PaymentStatus.SUCCESS
    return PaymentStatus.FAILED


def create_payment(
    db: Session,
    user: User,
    booking_id: int,
    simulate_outcome: PaymentStatus | None,
) -> tuple[Payment, Booking]:
    # Lock the booking row so two concurrent payments can't both run.
    booking = db.scalar(
        select(Booking)
        .where(Booking.id == booking_id, Booking.user_id == user.id)
        .with_for_update()
    )
    if booking is None:
        raise NotFoundError("Booking not found")
    if booking.status == BookingStatus.CONFIRMED:
        raise ConflictError("Booking is already paid")
    if booking.status == BookingStatus.CANCELLED:
        raise ConflictError("Booking is cancelled")
    # PENDING and FAILED bookings may (re)try payment.

    outcome = simulate_outcome or _roll_outcome()
    payment = Payment(
        booking_id=booking.id,
        amount=booking.amount,
        status=outcome,
        provider_reference=f"mock_{uuid.uuid4().hex}",
    )
    booking.status = (
        BookingStatus.CONFIRMED
        if outcome == PaymentStatus.SUCCESS
        else BookingStatus.FAILED
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    db.refresh(booking)
    logger.info(
        "payment_created payment_id=%s booking_id=%s status=%s",
        payment.id,
        booking.id,
        outcome.value,
    )
    return payment, booking


def process_webhook(db: Session, event: WebhookPayload, raw: dict) -> WebhookResult:
    """Apply a provider status update exactly once per event_id."""
    # Fast path: already handled.
    if db.scalar(
        select(WebhookEvent.id).where(WebhookEvent.event_id == event.event_id)
    ):
        logger.info("webhook_duplicate event_id=%s", event.event_id)
        return WebhookResult(status="duplicate")

    payment = db.scalar(
        select(Payment).where(Payment.provider_reference == event.provider_reference)
    )
    if payment is None:
        raise NotFoundError("Unknown provider_reference")

    # Serialise processing per booking; a concurrent duplicate waits here and
    # then trips the UNIQUE(event_id) constraint below.
    booking = db.scalar(
        select(Booking).where(Booking.id == payment.booking_id).with_for_update()
    )

    try:
        db.add(WebhookEvent(event_id=event.event_id, payload=raw))
        db.flush()
    except IntegrityError:
        db.rollback()
        logger.info("webhook_duplicate_race event_id=%s", event.event_id)
        return WebhookResult(status="duplicate")

    payment.status = event.status
    if booking.status != BookingStatus.CANCELLED:  # never resurrect a cancelled booking
        if event.status == PaymentStatus.SUCCESS:
            booking.status = BookingStatus.CONFIRMED
        else:
            other_success = db.scalar(
                select(func.count())
                .select_from(Payment)
                .where(
                    Payment.booking_id == booking.id,
                    Payment.status == PaymentStatus.SUCCESS,
                    Payment.id != payment.id,
                )
            )
            if not other_success:
                booking.status = BookingStatus.FAILED

    db.commit()
    logger.info(
        "webhook_processed event_id=%s payment_id=%s status=%s",
        event.event_id,
        payment.id,
        event.status.value,
    )
    return WebhookResult(status="processed", booking_status=booking.status)
