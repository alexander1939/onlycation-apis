from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.apis.deps import auth_required, get_db
from app.schemas.students.confirm_students_schema import (
    StudentConfirmationCreateRequest,
    StudentConfirmationCreateResponse,
    StudentConfirmationData
)
from app.services.students.confirm_students_service import create_confirmation_by_student

security = HTTPBearer()
router = APIRouter()

@router.post("/student/",
            response_model=StudentConfirmationCreateResponse,
            dependencies=[Depends(auth_required)])
async def confirm_student(
    confirmation_data: StudentConfirmationCreateRequest, 
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials

    confirmation = await create_confirmation_by_student(
    db=db,
    token=token,
    confirmation_value=confirmation_data.confirmation,
    payment_booking_id=confirmation_data.payment_booking_id
)


    return StudentConfirmationCreateResponse(
        success=True,
        message="Confirmación del estudiante registrada exitosamente",
        data=StudentConfirmationData(
            id=confirmation.id,
            teacher_id=confirmation.teacher_id,       # sacado del booking
            student_id=confirmation.student_id,       # del token
            payment_booking_id=confirmation.payment_booking_id,
            confirmation_date_student=confirmation.confirmation_date_student
        )
    )
