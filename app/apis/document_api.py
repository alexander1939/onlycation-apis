# apis/teachers/document_routes.py
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.apis.deps import auth_required, get_db
from app.services.teachers.document_service import (
    create_document_by_token, get_documents_by_token, get_user_id_from_token,
    update_document_by_token
)
from app.schemas.teachers.document_schema import DocumentCreateResponse, DocumentCreateData, DocumentReadResponse
from app.models import Document
from sqlalchemy import select
import os
from app.cores.security import decrypt_text
from app.cores.file_validator import FileValidator


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
        # Validar archivos antes de procesarlos
        await FileValidator.validate_file(certificate, file_type="pdf", max_size=10*1024*1024)
        await FileValidator.validate_file(curriculum, file_type="pdf", max_size=10*1024*1024)
        
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
                description=d.description,
                expertise_area=d.expertise_area,
                created_at=d.created_at
            ) for d in docs
        ]
    )

@router.get("/my-description/",
    dependencies=[Depends(auth_required)])
async def get_my_document_description(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Consultar solo la descripción del documento del usuario autenticado.
    No requiere document_id, se obtiene automáticamente del token.
    """
    token = credentials.credentials
    user_id = await get_user_id_from_token(token)
    
    q = await db.execute(
        select(Document).where(Document.user_id == user_id)
    )
    doc = q.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="No tienes documentos registrados")
    
    return {
        "success": True,
        "message": "Descripción obtenida exitosamente",
        "data": {
            "description": doc.description
        }
    }

@router.get("/my-expertise-area/",
    dependencies=[Depends(auth_required)])
async def get_my_document_expertise_area(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Consultar solo el área de especialidad del documento del usuario autenticado.
    No requiere document_id, se obtiene automáticamente del token.
    """
    token = credentials.credentials
    user_id = await get_user_id_from_token(token)
    
    q = await db.execute(
        select(Document).where(Document.user_id == user_id)
    )
    doc = q.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="No tienes documentos registrados")
    
    return {
        "success": True,
        "message": "Área de especialidad obtenida exitosamente",
        "data": {
            "expertise_area": doc.expertise_area
        }
    }

@router.put("/update/{document_id}/",
    response_model=DocumentCreateResponse,
    dependencies=[Depends(auth_required)])
async def update_document_route(
    document_id: int,
    rfc: str = Form(None),
    expertise_area: str = Form(None),
    description: str = Form(None),
    certificate: UploadFile = File(None),
    curriculum: UploadFile = File(None),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualizar un documento existente.
    Todos los campos son opcionales. Solo se actualizan los campos proporcionados.
    """
    try:
        # Validar archivos si se proporcionan
        if certificate:
            await FileValidator.validate_file(certificate, file_type="pdf", max_size=10*1024*1024)
        if curriculum:
            await FileValidator.validate_file(curriculum, file_type="pdf", max_size=10*1024*1024)
        
        token = credentials.credentials
        document = await update_document_by_token(
            db=db,
            token=token,
            document_id=document_id,
            rfc=rfc,
            expertise_area=expertise_area,
            description=description,
            certificate_file=certificate,
            curriculum_file=curriculum
        )
        
        return DocumentCreateResponse(
            success=True,
            message="Documento actualizado exitosamente",
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

@router.patch("/update-certificate/{document_id}/",
    response_model=DocumentCreateResponse,
    dependencies=[Depends(auth_required)])
async def update_certificate_route(
    document_id: int,
    certificate: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualizar solo el certificado de un documento.
    """
    try:
        await FileValidator.validate_file(certificate, file_type="pdf", max_size=10*1024*1024)
        
        token = credentials.credentials
        document = await update_document_by_token(
            db=db,
            token=token,
            document_id=document_id,
            certificate_file=certificate
        )
        
        return DocumentCreateResponse(
            success=True,
            message="Certificado actualizado exitosamente",
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

@router.patch("/update-curriculum/{document_id}/",
    response_model=DocumentCreateResponse,
    dependencies=[Depends(auth_required)])
async def update_curriculum_route(
    document_id: int,
    curriculum: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualizar solo el currículum de un documento.
    """
    try:
        await FileValidator.validate_file(curriculum, file_type="pdf", max_size=10*1024*1024)
        
        token = credentials.credentials
        document = await update_document_by_token(
            db=db,
            token=token,
            document_id=document_id,
            curriculum_file=curriculum
        )
        
        return DocumentCreateResponse(
            success=True,
            message="Currículum actualizado exitosamente",
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

@router.patch("/update-rfc/{document_id}/",
    response_model=DocumentCreateResponse,
    dependencies=[Depends(auth_required)])
async def update_rfc_route(
    document_id: int,
    rfc: str = Form(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualizar solo el RFC de un documento.
    """
    try:
        token = credentials.credentials
        document = await update_document_by_token(
            db=db,
            token=token,
            document_id=document_id,
            rfc=rfc
        )
        
        return DocumentCreateResponse(
            success=True,
            message="RFC actualizado exitosamente",
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

@router.patch("/update-description/{document_id}/",
    response_model=DocumentCreateResponse,
    dependencies=[Depends(auth_required)])
async def update_description_route(
    document_id: int,
    description: str = Form(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualizar solo la descripción de un documento.
    """
    try:
        token = credentials.credentials
        document = await update_document_by_token(
            db=db,
            token=token,
            document_id=document_id,
            description=description
        )
        
        return DocumentCreateResponse(
            success=True,
            message="Descripción actualizada exitosamente",
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

@router.patch("/update-expertise-area/{document_id}/",
    response_model=DocumentCreateResponse,
    dependencies=[Depends(auth_required)])
async def update_expertise_area_route(
    document_id: int,
    expertise_area: str = Form(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualizar solo el área de especialidad de un documento.
    """
    try:
        token = credentials.credentials
        document = await update_document_by_token(
            db=db,
            token=token,
            document_id=document_id,
            expertise_area=expertise_area
        )
        
        return DocumentCreateResponse(
            success=True,
            message="Área de especialidad actualizada exitosamente",
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
