from pydantic import BaseModel, EmailStr, constr

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetVerify(BaseModel):
    email: EmailStr
    code: str
    new_password: str