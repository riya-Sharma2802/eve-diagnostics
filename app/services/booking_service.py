import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models.models import Booking, BookingStatus, CentreTest, User
from app.schemas.booking import BookingCreate

logger = logging.getLogger(__name__)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:  # treat naive datetimes as UTC
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def create_booking(db: Session, user: User, data: BookingCreate) -> Booking:
    when = _as_utc(data.appointment_time)
    if when <= datetime.now(timezone.utc):
        raise UnprocessableError("appointment_time must be in the future")

    offering = db.scalar(
        select(CentreTest).where(
            CentreTest.centre_id == data.centre_id,
            CentreTest.test_id == data.test_id,
        )
    )
    if offering is None:
        raise NotFoundError("This test is not offered at the selected centre")

    booking = Booking(
        user_id=user.id,
        centre_id=data.centre_id,
        test_id=data.test_id,
        appointment_time=when,
        amount=offering.price,  # price snapshot
        status=BookingStatus.PENDING,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    logger.info("booking_created booking_id=%s user_id=%s", booking.id, user.id)
    return booking


def get_own_booking(db: Session, user: User, booking_id: int) -> Booking:
    # Someone else's booking is reported as 404 so IDs can't be probed.
    booking = db.scalar(
        select(Booking).where(Booking.id == booking_id, Booking.user_id == user.id)
    )
    if booking is None:
        raise NotFoundError("Booking not found")
    return booking


def list_own_bookings(
    db: Session,
    user: User,
    skip: int,
    limit: int,
    status: BookingStatus | None,
) -> tuple[list[Booking], int]:
    stmt = select(Booking).where(Booking.user_id == user.id)
    if status is not None:
        stmt = stmt.where(Booking.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Booking.id.desc()).offset(skip).limit(limit)
    ).all()
    return list(rows), total


def cancel_booking(db: Session, user: User, booking_id: int) -> Booking:
    booking = db.scalar(
        select(Booking)
        .where(Booking.id == booking_id, Booking.user_id == user.id)
        .with_for_update()
    )
    if booking is None:
        raise NotFoundError("Booking not found")
    if booking.status not in (BookingStatus.PENDING, BookingStatus.CONFIRMED):
        raise ConflictError(f"A {booking.status.value} booking cannot be cancelled")
    booking.status = BookingStatus.CANCELLED
    db.commit()
    db.refresh(booking)
    logger.info("booking_cancelled booking_id=%s", booking.id)
    return booking
