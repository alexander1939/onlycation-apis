from fastapi import APIRouter, Depends
from app.apis.deps import get_db, require_privilege
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.schemas.auths.login_schema import LoginRequest, LoginResponse
from app.schemas.privileges.privilege_shema import PrivilegeCreateRequest, PrivilegeUpdateRequest, PrivilegeResponse
from app.services.auths.login_service import login_user
from app.services.privileges.privilege_service import create_privilege_service, update_privilege_service


from fastapi import APIRouter, HTTPException


router = APIRouter()

@router.post("/create/", response_model=PrivilegeResponse)
async def create_privilege(
    request: PrivilegeCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_data = Depends(require_privilege("privilege", "create"))
):
    new_privilege = await create_privilege_service(db, request)
    return {
        "success": True,
        "message": "Privilege created successfully.",
        "data": {
            "id": new_privilege.id,
            "name": new_privilege.name,
            "action": new_privilege.action,
            "description": new_privilege.description
        }
    }

@router.put("/update/{privilege_id}", response_model=PrivilegeResponse)
async def update_privilege(
    privilege_id: int,
    request: PrivilegeUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_data = Depends(require_privilege("privilege", "edit"))
):
    updated_privilege = await update_privilege_service(db, privilege_id, request)
    return {
        "success": True,
        "message": "Privilege updated successfully.",
        "data": {
            "id": updated_privilege.id,
            "name": updated_privilege.name,
            "action": updated_privilege.action,
            "description": updated_privilege.description
        }
    }