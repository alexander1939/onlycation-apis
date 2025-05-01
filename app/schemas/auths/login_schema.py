from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: EmailStr
    first_name: str
    status: str 

class LoginResponse(BaseModel):
    success: bool
    message: str
    data: LoginData