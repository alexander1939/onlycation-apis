from pydantic import BaseModel, EmailStr, constr

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetVerify(BaseModel):
    code: str
    new_password: str

class PasswordResetCheckCode(BaseModel):
    code: str