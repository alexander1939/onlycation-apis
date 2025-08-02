from fastapi import APIRouter, Depends, HTTPException
from app.schemas.bookings.booking_shema import (
    BookingRequest, BookingPaymentResponse,
    VerifyBookingPaymentResponse
)
from app.services.bookings.booking_service import (
    create_booking_payment_session,
    verify_booking_payment_and_create_records,
    get_user_by_token  # importa la función
)
from app.apis.deps import auth_required, get_db
from sqlalchemy.ext.asyncio import AsyncSession

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
    result = await verify_booking_payment_and_create_records(db, session_id, user_data.get("user_id"))
    return result