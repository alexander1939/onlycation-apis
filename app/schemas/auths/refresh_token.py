from pydantic import BaseModel, EmailStr
from typing import Optional

class RefreshTokenRequest(BaseModel):
    token: str

class RefreshTokenData(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    email: EmailStr
    first_name: str
    last_name: str
    role: Optional[str] = None
    status: Optional[str] = None
    preference_id: Optional[int] = None

class RefreshTokenResponse(BaseModel):
    success: bool
    message: str
    data: RefreshTokenData
