from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class EducationalLevelBase(BaseModel):
    name: str = Field(..., max_length=100)
    status_id: Optional[int] = None

class EducationalLevelCreate(EducationalLevelBase):
    pass

class EducationalLevelUpdate(EducationalLevelBase):
    name: Optional[str] = Field(None, max_length=100)

class EducationalLevelInDB(EducationalLevelBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class EducationalLevel(EducationalLevelInDB):
    pass
