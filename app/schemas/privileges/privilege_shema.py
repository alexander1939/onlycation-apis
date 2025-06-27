from pydantic import BaseModel
from typing import Optional, List

class PrivilegeCreateRequest(BaseModel):
    name: str
    action: str
    description: str 
    status_id: int

class PrivilegeUpdateRequest(BaseModel):
    name: Optional[str] = None
    action: Optional[str] = None
    description: Optional[str] = None

class PrivilegeStatusRequest(BaseModel):
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

class PrivilegeListResponse(BaseModel):
    success: bool
    message: str
    data: List[PrivilegeData]
    total: int
    offset: int
    limit: int
    has_more: bool
