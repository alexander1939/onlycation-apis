from pydantic import BaseModel, EmailStr

class RegisterUserRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str

    class Config:
        from_attributes = True  # Cambiado de orm_mode a from_attributes
