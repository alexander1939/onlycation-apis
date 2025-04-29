from pydantic import BaseModel, EmailStr, ConfigDict

class RegisterUserRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str

    model_config = ConfigDict(from_attributes=True)
