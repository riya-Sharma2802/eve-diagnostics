from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.models import BookingStatus


class BookingCreate(BaseModel):
    centre_id: int
    test_id: int
    appointment_time: datetime


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    centre_id: int
    test_id: int
    appointment_time: datetime
    amount: Decimal
    status: BookingStatus
    created_at: datetime
