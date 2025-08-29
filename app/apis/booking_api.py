from fastapi import APIRouter, Depends, HTTPException
from app.schemas.bookings.booking_shema import (
    BookingRequest, BookingPaymentResponse,
    VerifyBookingPaymentResponse, RescheduleBookingRequest, RescheduleBookingResponse
)
from app.services.bookings.booking_service import get_user_by_token
from app.services.bookings.stripe_session_service import create_booking_payment_session
from app.services.bookings.payment_verification_service import verify_booking_payment_and_create_records
from app.services.bookings.reschedule_service import reschedule_booking, get_available_slots_for_teacher
from app.apis.deps import auth_required, get_db
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

router = APIRouter()

@router.post("/crear-booking/", response_model=BookingPaymentResponse, dependencies=[Depends(auth_required)])
async def crear_booking(
    request: BookingRequest,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    user = await get_user_by_token(db, user_data.get("user_id"))  
    result = await create_booking_payment_session(db, user, request)
    return {
        "success": True,
        "message": "Sesión de pago creada exitosamente",
        "data": result
    }

@router.get("/verificar-booking/{session_id}", response_model=VerifyBookingPaymentResponse, dependencies=[Depends(auth_required)])
async def verificar_booking(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    booking_data = await verify_booking_payment_and_create_records(db, session_id, user_data.get("user_id"))
    return {
        "success": True,
        "message": "Booking payment verified successfully",
        "payment_status": "completed",
        "data": booking_data
    }

@router.put("/reagendar-booking/", response_model=RescheduleBookingResponse, dependencies=[Depends(auth_required)])
async def reagendar_booking(
    request: RescheduleBookingRequest,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    """
    Reagenda una reserva existente a un nuevo horario disponible del docente.
    Solo se puede reagendar hasta 30 minutos antes de la clase.
    """
    booking_data = await reschedule_booking(
        db=db,
        student_id=user_data.get("user_id"),
        booking_id=request.booking_id,
        new_availability_id=request.new_availability_id,
        new_start_time=request.new_start_time,
        new_end_time=request.new_end_time
    )
    
    return {
        "success": True,
        "message": "Reserva reagendada exitosamente",
        "data": booking_data
    }
