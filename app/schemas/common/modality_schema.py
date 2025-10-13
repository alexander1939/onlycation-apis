from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ModalityBase(BaseModel):
    name: str = Field(..., max_length=100)
    status_id: Optional[int] = None

class ModalityCreate(ModalityBase):
    pass

class ModalityUpdate(ModalityBase):
    name: Optional[str] = Field(None, max_length=100)

class ModalityInDB(ModalityBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Modality(ModalityInDB):
    pass
