from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi.responses import StreamingResponse
import io


from fastapi import Form, File, UploadFile, HTTPException
from typing import Optional

from app.apis.deps import auth_required, get_db
from app.schemas.students.confirm_students_schema import (
    StudentConfirmationCreateRequest,
    StudentConfirmationCreateResponse,
    StudentConfirmationData
)
from app.services.students.confirm_students_service import create_confirmation_by_student
from app.services.students.confirm_students_service import get_student_evidence

security = HTTPBearer()
router = APIRouter()

@router.post("/student/{payment_booking_id}",
            response_model=StudentConfirmationCreateResponse,
            dependencies=[Depends(auth_required)])
async def confirm_student(
    payment_booking_id: int,
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
        payment_booking_id=payment_booking_id,   
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



@router.get("/student/evidence/{confirmation_id}")
async def get_student_evidence_api(
    confirmation_id: int,
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    # Obtener bytes desencriptados desde el service
    evidence_bytes, filename = await get_student_evidence(db, token, confirmation_id)

    # Retornar como archivo descargable
    return StreamingResponse(
        io.BytesIO(evidence_bytes),
        media_type="image/jpeg",  # o detectar dinámicamente
        headers={
            "Content-Disposition": f"inline; filename={filename}"
        }
    )