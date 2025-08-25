from fastapi import APIRouter, Depends, Form, File, UploadFile, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.apis.deps import auth_required, get_db
from app.schemas.teachers.confirm_teacher_schema import (
    ConfirmationCreateResponse,
    ConfirmationData
)
from app.services.teachers.confirm_teacher_service import create_confirmation_by_teacher

security = HTTPBearer()
router = APIRouter()

@router.post("/teacher/", response_model=ConfirmationCreateResponse, dependencies=[Depends(auth_required)])
async def confirm_teacher(
    confirmation: bool = Form(...),
    evidence_file: UploadFile = File(None),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials

    # Pasamos todo al service, incluyendo el archivo
    confirmation_obj = await create_confirmation_by_teacher(
        db=db,
        token=token,
        confirmation_value=confirmation,
        student_id=0,       # si quieres puedes pasar dinámico desde el request
        payment_booking_id=1,  # idem
        evidence_file=evidence_file
    )

    return ConfirmationCreateResponse(
        success=True,
        message="Confirmación del docente registrada exitosamente",
        data=ConfirmationData(
            id=confirmation_obj.id,
            teacher_id=confirmation_obj.teacher_id,
            student_id=confirmation_obj.student_id,
            payment_booking_id=confirmation_obj.payment_booking_id,
            confirmation_date_teacher=confirmation_obj.confirmation_date_teacher,
            evidence_teacher=confirmation_obj.evidence_teacher
        )
    )
