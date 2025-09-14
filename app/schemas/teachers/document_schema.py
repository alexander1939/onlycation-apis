# app/schemas/teachers/document_schema.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DocumentCreateRequest(BaseModel):
    rfc: str
    expertise_area: str

class DocumentCreateData(BaseModel):
    id: int
    user_id: int
    rfc: str  # devolveremos "***PROTEGIDO***"
    certificate: str  # endpoint de descarga
    curriculum: str   # endpoint de descarga
    expertise_area: str
    created_at: datetime

class DocumentCreateResponse(BaseModel):
    success: bool
    message: str
    data: DocumentCreateData

class DocumentReadResponse(BaseModel):
    success: bool
    message: str
    data: Optional[list[DocumentCreateData]]
