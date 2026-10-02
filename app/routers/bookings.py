from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user
from app.models.models import BookingStatus, User
from app.schemas.booking import BookingCreate, BookingOut
from app.schemas.common import Page
from app.services import booking_service as svc

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("/", response_model=BookingOut, status_code=201)
def create_booking(
    payload: BookingCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return svc.create_booking(db, user, payload)


@router.get("/", response_model=Page[BookingOut])
def list_my_bookings(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: BookingStatus | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows, total = svc.list_own_bookings(db, user, skip, limit, status)
    return Page[BookingOut](
        items=[BookingOut.model_validate(b) for b in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(
    booking_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return svc.get_own_booking(db, user, booking_id)


@router.post("/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(
    booking_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return svc.cancel_booking(db, user, booking_id)
