from fastapi import APIRouter, Depends, Form, File, UploadFile, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi.responses import StreamingResponse
import io

from app.apis.deps import auth_required, get_db
from app.schemas.teachers.confirm_teacher_schema import (
    ConfirmationCreateResponse,
    ConfirmationData
)
from app.services.teachers.confirm_teacher_service import create_confirmation_by_teacher
from app.services.teachers.confirm_teacher_service import get_teacher_evidence


security = HTTPBearer()
router = APIRouter()

@router.post("/teacher/", response_model=ConfirmationCreateResponse, dependencies=[Depends(auth_required)])
async def confirm_teacher(
    confirmation: bool = Form(...),
    description_teacher: str = Form(...),   # 🔹 Nuevo campo obligatorio
    evidence_file: UploadFile = File(...),
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
        evidence_file=evidence_file,
        description_teacher=description_teacher
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
            evidence_teacher=confirmation_obj.evidence_teacher,
            description_teacher=confirmation_obj.description_teacher
        )
    )


@router.get("/teacher/evidence/{confirmation_id}")
async def get_teacher_evidence_api(
    confirmation_id: int,
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    # Obtener bytes desencriptados desde el service
    evidence_bytes, filename = await get_teacher_evidence(db, token, confirmation_id)

    # Retornar como archivo descargable
    return StreamingResponse(
        io.BytesIO(evidence_bytes),
        media_type="image/jpeg",  # o detectar dinámicamente
        headers={
            "Content-Disposition": f"inline; filename={filename}"
        }
    )