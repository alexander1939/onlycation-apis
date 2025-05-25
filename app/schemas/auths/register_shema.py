from pydantic import BaseModel, EmailStr, ConfigDict

"""
Modelo que representa la estructura de datos recibida y enviara en una solicitud den las apis de register
"""
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
    email: EmailStr


class RegisterUserResponse(BaseModel):
    success: bool
    message: str
    data: RegisterUserData