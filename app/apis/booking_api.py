from fastapi import APIRouter, Depends, HTTPException
from app.schemas.bookings.booking_shema import (
    BookingRequest, BookingPaymentResponse,
    VerifyBookingPaymentResponse, RescheduleBookingRequest, RescheduleBookingResponse
)
from app.schemas.bookings.reschedule_request_schema import (
    TeacherRescheduleRequestCreate, StudentRescheduleResponse
)
from app.services.bookings.booking_service import get_user_by_token
from app.services.bookings.stripe_session_service import create_booking_payment_session
from app.services.bookings.payment_verification_service import verify_booking_payment_and_create_records
from app.services.bookings.reschedule_service import reschedule_booking, get_available_slots_for_teacher
from app.services.bookings.teacher_reschedule_service import (
    create_teacher_reschedule_request, get_teacher_reschedule_requests
)
from app.services.bookings.student_reschedule_service import (
    get_student_reschedule_requests, respond_to_reschedule_request
)
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

# TEACHER RESCHEDULE REQUEST ENDPOINTS
@router.post("/solicitar-reagendado/", dependencies=[Depends(auth_required)])
async def solicitar_reagendado(
    request_data: TeacherRescheduleRequestCreate,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    """
    Endpoint para que el docente solicite reagendar una reserva
    """
    result = await create_teacher_reschedule_request(
        db=db,
        teacher_id=user_data.get("user_id"),
        booking_id=request_data.booking_id,
        new_availability_id=request_data.new_availability_id,
        new_start_time=request_data.new_start_time,
        new_end_time=request_data.new_end_time,
        reason=request_data.reason
    )
    
    return {
        "success": True,
        "message": "Solicitud de reagendado enviada al estudiante",
        "data": result
    }

@router.get("/mis-solicitudes-reagendado/", dependencies=[Depends(auth_required)])
async def mis_solicitudes_reagendado(
    offset: int = 0,
    limit: int = 6,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    """
    Obtener todas las solicitudes de reagendado del docente con paginación
    """
    result = await get_teacher_reschedule_requests(
        db, 
        user_data.get("user_id"),
        offset=offset,
        limit=limit
    )
    
    return {
        "success": True,
        "message": "Solicitudes de reagendado obtenidas exitosamente",
        "data": result
    }

# STUDENT RESCHEDULE RESPONSE ENDPOINTS
@router.get("/solicitudes-reagendado-pendientes/", dependencies=[Depends(auth_required)])
async def solicitudes_reagendado_pendientes(
    offset: int = 0,
    limit: int = 6,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    """
    Obtener todas las solicitudes de reagendado pendientes para el estudiante con paginación
    """
    result = await get_student_reschedule_requests(
        db, 
        user_data.get("user_id"),
        offset=offset,
        limit=limit
    )
    
    return {
        "success": True,
        "message": "Solicitudes de reagendado obtenidas exitosamente",
        "data": result
    }

@router.post("/responder-reagendado/", dependencies=[Depends(auth_required)])
async def responder_reagendado(
    response_data: StudentRescheduleResponse,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    """
    Responder a una solicitud de reagendado (aprobar o rechazar)
    """
    result = await respond_to_reschedule_request(
        db=db,
        student_id=user_data.get("user_id"),
        request_id=response_data.request_id,
        approved=response_data.approved,
        response_message=response_data.response_message
    )
    
    action = "aprobada" if response_data.approved else "rechazada"
    
    return {
        "success": True,
        "message": f"Solicitud de reagendado {action} exitosamente",
        "data": result
    }
