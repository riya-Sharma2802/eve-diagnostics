import json
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.models import BookingStatus, PaymentStatus
from app.schemas.booking import BookingOut


class PaymentCreate(BaseModel):
    booking_id: int
    # Mock-only knob: force the outcome (handy for demos and tests).
    simulate_outcome: PaymentStatus | None = None


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    amount: Decimal
    status: PaymentStatus
    provider_reference: str
    created_at: datetime


class PaymentResult(BaseModel):
    payment: PaymentOut
    booking: BookingOut


class WebhookPayload(BaseModel):
    event_id: str = Field(min_length=1, max_length=100)
    provider_reference: str = Field(min_length=1, max_length=100)
    status: PaymentStatus


class WebhookResult(BaseModel):
    status: Literal["processed", "duplicate"]
    booking_status: BookingStatus | None = None
