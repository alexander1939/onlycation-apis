from pydantic import BaseModel, EmailStr, ConfigDict

class RegisterUserRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    privacy_policy_accepted: bool
    
    model_config = ConfigDict(from_attributes=True)

class RegisterUserData(BaseModel):
    first_name: str
    last_name: str
    emails: EmailStr


class RegisterUserResponse(BaseModel):
    success: bool
    message: str
    data: RegisterUserData