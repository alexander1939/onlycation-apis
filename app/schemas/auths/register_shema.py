from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from app.cores.input_validator import sanitize_string_field

"""
Modelo que representa la estructura de datos recibida y enviara en una solicitud den las apis de register
"""
class RegisterUserRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    privacy_policy_accepted: bool
    
    # Validadores para sanitizar inputs y prevenir XSS
    _sanitize_first_name = field_validator('first_name')(sanitize_string_field)
    _sanitize_last_name = field_validator('last_name')(sanitize_string_field)
    
    model_config = ConfigDict(from_attributes=True)

class RegisterUserData(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr


class RegisterUserResponse(BaseModel):
    success: bool
    message: str
    data: RegisterUserData