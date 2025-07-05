from pydantic import BaseModel, Field
from typing import Optional, List

class PrivilegeCreateRequest(BaseModel):
    name: str
    action: str
    description: str 
    status_id: int

class PrivilegeUpdateRequest(BaseModel):
    name: str
    action: str
    description: str

class PrivilegeStatusRequest(BaseModel):
    status_id: int = Field(..., description="Only status_id is allowed")

class PrivilegeData(BaseModel):
    id: int
    name: str
    action: str
    description: str 

class PrivilegeDataWithStatus(BaseModel):
    id: int
    name: str
    action: str
    description: str
    status_id: int

class PrivilegeResponse(BaseModel):
    success: bool
    message: str
    data: PrivilegeData

class PrivilegeStatusResponse(BaseModel):
    success: bool
    message: str
    data: PrivilegeDataWithStatus

class PrivilegeListResponse(BaseModel):
    success: bool
    message: str
    data: List[PrivilegeData]
    total: int
    offset: int
    limit: int
    has_more: bool
