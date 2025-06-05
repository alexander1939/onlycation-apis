from pydantic import BaseModel,EmailStr
from typing import Optional

class LogoutRequest(BaseModel):
    email: EmailStr


class DefaultResponse(BaseModel):
    success: bool
    message: str
