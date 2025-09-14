from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

class TimeSlot(BaseModel):
    start_time: str  # "09:00"
    end_time: str    # "10:00"
    datetime_start: str  # ISO format
    datetime_end: str    # ISO format
    status: str      # "available", "occupied", "pending"
    availability_id: Optional[int] = None
    duration_hours: int = 1

class DayAvailability(BaseModel):
    date: str  # "2025-09-03"
    day_name: str  # "Lunes"
    slots: List[TimeSlot]

class TeacherWeeklyAgenda(BaseModel):
    teacher_id: int
    teacher_name: str
    week_start: str  # "2025-09-02" (Monday)
    week_end: str    # "2025-09-08" (Sunday)
    days: List[DayAvailability]

class TeacherAgendaResponse(BaseModel):
    success: bool
    message: str
    data: TeacherWeeklyAgenda

class AvailabilitySummary(BaseModel):
    teacher_id: int
    teacher_name: str
    period_days: int
    total_hours_available: float
    total_hours_booked: float
    total_hours_free: float
    availability_percentage: float
    total_bookings: int

class AvailabilitySummaryResponse(BaseModel):
    success: bool
    message: str
    data: AvailabilitySummary

class WeeklyAvailabilityRequest(BaseModel):
    week_start_date: Optional[str] = None  # "2025-09-02" (Monday)
    
class AvailabilityStatsRequest(BaseModel):
    days_ahead: Optional[int] = 30
