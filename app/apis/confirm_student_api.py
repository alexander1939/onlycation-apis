from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Form, File, UploadFile, HTTPException
from typing import Optional

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
    confirmation: bool = Form(...),          
    description_student: str = Form(...),   # 🔹 Nuevo campo obligatorio      
    evidence_file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials

    confirmation_obj = await create_confirmation_by_student(
        db=db,
        token=token,
        confirmation_value=confirmation,
        payment_booking_id=1,   
        evidence_file=evidence_file,
        description_student=description_student   # 🔹 Se pasa al service
    )

    return StudentConfirmationCreateResponse(
        success=True,
        message="Confirmación del estudiante registrada exitosamente",
        data=StudentConfirmationData(
            id=confirmation_obj.id,
            teacher_id=confirmation_obj.teacher_id,
            student_id=confirmation_obj.student_id,
            payment_booking_id=confirmation_obj.payment_booking_id,
            confirmation_date_student=confirmation_obj.confirmation_date_student,
            description_student=confirmation_obj.description_student
        )
    )
