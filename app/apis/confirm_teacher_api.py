from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.apis.deps import auth_required, get_db
from app.schemas.teachers.confirm_teacher_schema import (
    ConfirmationCreateRequest,
    ConfirmationCreateResponse,
    ConfirmationData
)
from app.services.teachers.confirm_teacher_service import create_confirmation_by_teacher

security = HTTPBearer()
router = APIRouter()

@router.post("/teacher/",
            response_model=ConfirmationCreateResponse,
            dependencies=[Depends(auth_required)])
async def confirm_teacher(
    confirmation_data: ConfirmationCreateRequest,  # aquí solo trae el booleano
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    confirmation = await create_confirmation_by_teacher(
    db=db,
    token=token,
    confirmation_value=confirmation_data.confirmation,
    student_id=confirmation_data.student_id,
    payment_booking_id=confirmation_data.payment_booking_id
)


    return ConfirmationCreateResponse(
    success=True,
    message="Confirmación del docente registrada exitosamente",
    data=ConfirmationData(
        id=confirmation.id,
        teacher_id=confirmation.teacher_id,
        student_id=confirmation.student_id,               # 👈 faltaba
        payment_booking_id=confirmation.payment_booking_id, # 👈 faltaba
        confirmation_date_teacher=confirmation.confirmation_date_teacher
    )
)
