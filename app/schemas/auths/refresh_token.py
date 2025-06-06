from pydantic import BaseModel

class RefreshTokenRequest(BaseModel):
    token: str

class RefreshTokenData(BaseModel):
    access_token: str
    token_type: str

class RefreshTokenResponse(BaseModel):
    success: bool
    message: str
    data: RefreshTokenData
