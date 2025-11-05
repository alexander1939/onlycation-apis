import os
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile
from app.models import Document, User
from app.cores.token import verify_token
from app.cores.security import (
    rfc_hash_plain, encrypt_text, encrypt_bytes
)

UPLOAD_DIR = "uploads/documents"

# -------- Validaciones --------

async def _validate_user_exists(db: AsyncSession, user_id: int):
    q = await db.execute(select(User).where(User.id == user_id))
    if not q.scalar_one_or_none():
        raise ValueError(f"El usuario con ID {user_id} no existe")

async def _validate_no_existing_document(db: AsyncSession, user_id: int):
    q = await db.execute(select(Document).where(Document.user_id == user_id))
    if q.scalar_one_or_none():
        raise ValueError("Ya has subido documentos. Solo puedes hacerlo una vez.")

async def _validate_unique_rfc_hash(db: AsyncSession, rfc_hash: str):
    q = await db.execute(select(Document).where(Document.rfc_hash == rfc_hash))
    if q.scalar_one_or_none():
        raise ValueError("Este RFC ya está registrado")

async def _validate_text_field(value: str, field_name: str):
    if not value or not value.strip():
        raise ValueError(f"El campo {field_name} es obligatorio")

async def _validate_file(file: UploadFile, field_name: str):
    if not file:
        raise ValueError(f"El archivo {field_name} es obligatorio")
    if not file.filename.lower().endswith(".pdf"):
        raise ValueError(f"El archivo {field_name} debe ser un PDF")
    # no leemos aquí para no consumir memoria, validaremos tamaño al guardar si quieres

async def _validate_description(value: str, field_name: str = "Descripción"):
    if not value or not value.strip():
        raise ValueError(f"El campo {field_name} es obligatorio")
    if len(value.strip()) < 10:
        raise ValueError(f"El campo {field_name} debe tener al menos 10 caracteres")
    if len(value.strip()) > 500:
        raise ValueError(f"El campo {field_name} no puede exceder los 500 caracteres")

# -------- Token --------

async def get_user_id_from_token(token: str) -> int:
    payload = verify_token(token)
    user_id = payload.get("user_id")
    if not user_id:
        raise ValueError("Token inválido: falta user_id")
    return user_id

# -------- Archivos cifrados --------

async def _save_encrypted_file(file: UploadFile, folder: str) -> str:
    os.makedirs(folder, exist_ok=True)
    raw = await file.read()
    if len(raw) == 0:
        raise ValueError(f"El archivo {file.filename} está vacío")
    from app.cores.security import encrypt_bytes
    enc = encrypt_bytes(raw)

    # Guardamos como .enc
    basename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}.enc"
    path = os.path.join(folder, basename)
    with open(path, "wb") as f:
        f.write(enc)

    # Reposicionar para evitar problemas si se reusa el UploadFile
    await file.seek(0)
    return path

# -------- Lógica principal --------

async def create_document_by_token(
    db: AsyncSession,
    token: str,
    rfc: str,
    expertise_area: str,
    certificate_file: UploadFile,
    curriculum_file: UploadFile,
    description: str
) -> Document:
    user_id = await get_user_id_from_token(token)

    # Validaciones
    await _validate_user_exists(db, user_id)
    await _validate_no_existing_document(db, user_id)
    await _validate_text_field(rfc, "RFC")
    await _validate_text_field(expertise_area, "Área de especialidad")
    await _validate_description(description, "Descripción")
    await _validate_file(certificate_file, "Certificado")
    await _validate_file(curriculum_file, "Currículum")

    # Hash + cifrado del RFC
    rfc_hash = rfc_hash_plain(rfc)
    await _validate_unique_rfc_hash(db, rfc_hash)
    rfc_cipher = encrypt_text(rfc.strip().upper())

    # Guardar archivos cifrados
    certificate_path = await _save_encrypted_file(certificate_file, UPLOAD_DIR)
    curriculum_path  = await _save_encrypted_file(curriculum_file,  UPLOAD_DIR)

    # Crear registro
    db_document = Document(
        user_id=user_id,
        rfc_hash=rfc_hash,
        rfc_cipher=rfc_cipher,
        certificate=certificate_path,  # .enc
        curriculum=curriculum_path,    # .enc
        expertise_area=expertise_area.strip(),
        description=description.strip(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(db_document)
    await db.commit()
    await db.refresh(db_document)
    return db_document

async def get_documents_by_token(db: AsyncSession, token: str) -> list[Document]:
    user_id = await get_user_id_from_token(token)
    res = await db.execute(select(Document).where(Document.user_id == user_id))
    return res.scalars().all()

async def update_document_by_token(
    db: AsyncSession,
    token: str,
    document_id: int,
    rfc: str = None,
    expertise_area: str = None,
    description: str = None,
    certificate_file: UploadFile = None,
    curriculum_file: UploadFile = None
) -> Document:
    """
    Actualizar un documento existente. Los archivos son opcionales.
    Si se envían nuevos archivos, se reemplazan los antiguos.
    """
    user_id = await get_user_id_from_token(token)
    
    # Obtener documento existente y verificar propiedad
    q = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id
        )
    )
    document = q.scalar_one_or_none()
    if not document:
        raise ValueError("Documento no encontrado o no tienes permisos para actualizarlo")
    
    # Actualizar campos de texto si se proporcionan
    if rfc is not None:
        await _validate_text_field(rfc, "RFC")
        # Verificar que el nuevo RFC no esté ya registrado (excepto el actual)
        new_rfc_hash = rfc_hash_plain(rfc)
        if new_rfc_hash != document.rfc_hash:
            await _validate_unique_rfc_hash(db, new_rfc_hash)
            document.rfc_hash = new_rfc_hash
            document.rfc_cipher = encrypt_text(rfc.strip().upper())
    
    if expertise_area is not None:
        await _validate_text_field(expertise_area, "Área de especialidad")
        document.expertise_area = expertise_area.strip()
    
    if description is not None:
        await _validate_description(description, "Descripción")
        document.description = description.strip()
    
    # Actualizar archivos si se proporcionan
    if certificate_file is not None:
        await _validate_file(certificate_file, "Certificado")
        # Eliminar archivo anterior si existe
        if document.certificate and os.path.exists(document.certificate):
            os.remove(document.certificate)
        # Guardar nuevo archivo cifrado
        document.certificate = await _save_encrypted_file(certificate_file, UPLOAD_DIR)
    
    if curriculum_file is not None:
        await _validate_file(curriculum_file, "Currículum")
        # Eliminar archivo anterior si existe
        if document.curriculum and os.path.exists(document.curriculum):
            os.remove(document.curriculum)
        # Guardar nuevo archivo cifrado
        document.curriculum = await _save_encrypted_file(curriculum_file, UPLOAD_DIR)
    
    document.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(document)
    return document
