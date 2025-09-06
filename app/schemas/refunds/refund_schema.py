from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class RefundRequestSchema(BaseModel):
    confirmation_id: int

class RefundResponseSchema(BaseModel):
    success: bool
    message: str
    confirmation_id: int
    refund_amount: Optional[float] = None
    stripe_refund_id: Optional[str] = None
    refund_request_id: Optional[int] = None
    estimated_refund_days: Optional[str] = None
    processed_automatically: bool = False
    note: Optional[str] = None

class RefundableBookingSchema(BaseModel):
    confirmation_id: int
    teacher_name: str
    class_date: str
    class_end_date: str
    refund_amount: float
    refund_type: str
    reason: str
    minutes_until_class: int
    hours_since_class_ended: float
    booking_date: str
    teacher_confirmed: bool

class RefundableBookingsResponseSchema(BaseModel):
    success: bool
    refundable_bookings: list[RefundableBookingSchema]
    total_count: int
    rules: dict
