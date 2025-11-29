from pydantic import BaseModel, Field
from typing import Optional

class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Nuevo nombre del usuario"
    )
    last_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Nuevo apellido del usuario"
    )

class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str

    class Config:
        from_attributes = True
