# apis/teachers/document_routes.py
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.apis.deps import auth_required, get_db
from app.services.teachers.document_service import (
    create_document_by_token, get_documents_by_token, get_user_id_from_token
)
from app.schemas.teachers.document_schema import DocumentCreateResponse, DocumentCreateData, DocumentReadResponse
from app.models import Document
from sqlalchemy import select
import os
from app.cores.security import decrypt_text


router = APIRouter()
security = HTTPBearer()

@router.post("/create/",
    response_model=DocumentCreateResponse,
    dependencies=[Depends(auth_required)])
async def create_document_route(
    rfc: str = Form(...),
    expertise_area: str = Form(...),
    description: str = Form(...),
    certificate: UploadFile = File(...),
    curriculum: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    try:
        token = credentials.credentials
        document = await create_document_by_token(
            db=db,
            token=token,
            rfc=rfc,
            expertise_area=expertise_area,
            certificate_file=certificate,  # ← Nota: el parámetro se llama certificate_file
            curriculum_file=curriculum,    # ← Nota: el parámetro se llama curriculum_file
            description=description
            )
        # No exponemos RFC ni paths; devolvemos solo metadatos
        return DocumentCreateResponse(
            success=True,
            message="Documento creado exitosamente",
            data=DocumentCreateData(
                id=document.id,
                user_id=document.user_id,
                rfc=document.rfc_cipher,
                certificate=f"/api/documents/{document.id}/download/certificate",
                curriculum=f"/api/documents/{document.id}/download/curriculum",
                description=document.description,
                expertise_area=document.expertise_area,
                created_at=document.created_at
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/read/",
    response_model=DocumentReadResponse,
    dependencies=[Depends(auth_required)])
async def read_documents_route(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    docs = await get_documents_by_token(db, token)
    return DocumentReadResponse(
        success=True,
        message="Lista de documentos",
        data=[
            DocumentCreateData(
                id=d.id,
                user_id=d.user_id,
                rfc=decrypt_text(d.rfc_cipher),
                certificate=f"/api/documents/{d.id}/download/certificate",
                curriculum=f"/api/documents/{d.id}/download/curriculum",
                expertise_area=d.expertise_area,
                created_at=d.created_at
            ) for d in docs
        ]
    )

# -------- Descarga segura (descifra al vuelo) --------

@router.get("/{document_id}/download/{kind}",
            dependencies=[Depends(auth_required)])
async def download_document_route(
    document_id: int,
    kind: str,  # "certificate" | "curriculum"
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    user_id = await get_user_id_from_token(token)

    q = await db.execute(select(Document).where(Document.id == document_id, Document.user_id == user_id))
    doc = q.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    path = doc.certificate if kind == "certificate" else doc.curriculum if kind == "curriculum" else None
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    from app.cores.security import decrypt_bytes

    def file_iterator():
        with open(path, "rb") as f:
            enc = f.read()
        dec = decrypt_bytes(enc)
        yield dec

    # mandamos como PDF
    filename = os.path.basename(path).replace(".enc", "") or f"{kind}.pdf"
    return StreamingResponse(file_iterator(), media_type="application/pdf",
                             headers={"Content-Disposition": f'inline; filename="{filename}"'})
