from fastapi import APIRouter, Depends, Form, File, UploadFile, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi.responses import StreamingResponse
import io

from app.apis.deps import auth_required, get_db
from app.schemas.teachers.confirm_teacher_schema import (
    ConfirmationCreateResponse,
    ConfirmationData,
    TeacherConfirmationRecentHistoryResponse,
    TeacherConfirmationAllHistoryResponse,
    ConfirmationDetailResponse,
)
from app.services.teachers.confirm_teacher_service import create_confirmation_by_teacher
from app.services.teachers.confirm_teacher_service import get_teacher_evidence
from app.services.teachers.confirm_teacher_service import (
    list_teacher_confirmations_recent,
    list_teacher_confirmations_all,
    get_confirmation_detail,
    list_teacher_confirmations_by_date,
    get_confirmation_evidence_for_viewer
)


security = HTTPBearer()
router = APIRouter()

@router.post("/teacher/{payment_booking_id}", response_model=ConfirmationCreateResponse, dependencies=[Depends(auth_required)])
async def confirm_teacher(
    payment_booking_id: int,
    confirmation: bool = Form(...),
    description_teacher: str = Form(...),   # Nuevo campo obligatorio
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
        #student_id=0,       # si quieres puedes pasar dinámico desde el request
        payment_booking_id=payment_booking_id,  # idem
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


@router.get(
    "/teacher/history/recent",
    response_model=TeacherConfirmationRecentHistoryResponse,
    dependencies=[Depends(auth_required)]
)
async def get_teacher_recent_confirmations(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve SOLO confirmaciones confirmables para el docente (clase terminada y ventana abierta),
    ordenadas por más recientes. La ventana sigue la política vigente del servicio de confirmación del docente.
    """
    token = credentials.credentials
    items = await list_teacher_confirmations_recent(db, token)
    return {"success": True, "items": items}


@router.get(
    "/teacher/history/all",
    response_model=TeacherConfirmationAllHistoryResponse,
    dependencies=[Depends(auth_required)]
)
async def get_teacher_all_confirmations(
    offset: int = 0,
    limit: int = 10,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Lista TODAS las confirmaciones del docente (paginado con offset/limit)."""
    token = credentials.credentials
    data = await list_teacher_confirmations_all(db, token, offset=offset, limit=limit)
    return {
        "success": True,
        "offset": data["offset"],
        "limit": data["limit"],
        "total": data["total"],
        "has_more": data["has_more"],
        "items": data["items"],
    }


@router.get(
    "/teacher/history/by-date",
    response_model=TeacherConfirmationRecentHistoryResponse,
    dependencies=[Depends(auth_required)]
)
async def get_teacher_confirmations_by_date(
    date: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Filtra confirmaciones del docente por fecha de booking (día completo).
    Acepta formatos YYYY-MM-DD o DD/MM/YYYY. Usa zona America/Mexico_City para los límites del día.
    """
    token = credentials.credentials
    items = await list_teacher_confirmations_by_date(db, token, date)
    return {"success": True, "items": items}


@router.get(
    "/detail/{confirmation_id}",
    response_model=ConfirmationDetailResponse,
    dependencies=[Depends(auth_required)]
)
async def get_confirmation_detail_api(
    confirmation_id: int,
    download: bool = False,
    side: str | None = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    token = credentials.credentials
    # Si se solicita descarga, devolver archivo de evidencia del dueño (o del 'side' indicado)
    if download:
        evidence_bytes, filename = await get_confirmation_evidence_for_viewer(db, token, confirmation_id, side=side)
        return StreamingResponse(
            io.BytesIO(evidence_bytes),
            media_type="image/jpeg",  # TODO: detectar dinámicamente por extensión
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    # Si no, devolver solo metadatos
    data = await get_confirmation_detail(db, token, confirmation_id)
    return {"success": True, "data": data}


@router.get("/evidence/{confirmation_id}")
async def get_confirmation_evidence_api(
    confirmation_id: int,
    download: bool = False,
    side: str | None = None,
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Descarga o muestra la evidencia correspondiente al usuario autenticado.
    - Si el viewer es el docente dueño de la confirmación -> retorna evidencia del docente.
    - Si el viewer es el alumno dueño -> retorna evidencia del alumno.
    - En otro caso -> 403.
    Usa ?download=true para forzar descarga (attachment).
    """
    token = credentials.credentials
    evidence_bytes, filename = await get_confirmation_evidence_for_viewer(db, token, confirmation_id, side=side)
    disposition = "attachment" if download else "inline"
    return StreamingResponse(
        io.BytesIO(evidence_bytes),
        media_type="image/jpeg",  # TODO: detectar dinámicamente por extensión
        headers={
            "Content-Disposition": f"{disposition}; filename={filename}"
        }
    )