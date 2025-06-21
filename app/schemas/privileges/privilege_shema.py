from pydantic import BaseModel
from typing import Optional

class PrivilegeCreateRequest(BaseModel):
    name: str
    action: str
    description: str 
    status_id: int

class PrivilegeData(BaseModel):
    id: int
    name: str
    action: str
    description: str 

class PrivilegeResponse(BaseModel):
    success: bool
    message: str
    data: PrivilegeData
