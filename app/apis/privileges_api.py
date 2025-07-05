from fastapi import APIRouter, Depends
from app.apis.deps import get_db, require_privilege
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.schemas.auths.login_schema import LoginRequest, LoginResponse
from app.schemas.privileges.privilege_shema import PrivilegeCreateRequest, PrivilegeUpdateRequest, PrivilegeStatusRequest, PrivilegeResponse, PrivilegeStatusResponse, PrivilegeListResponse
from app.services.auths.login_service import login_user
from app.services.privileges.privilege_service import create_privilege_service, update_privilege_service, get_privilege_service, get_all_privileges_service, change_privilege_status_service


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
    user_data = Depends(require_privilege("privilege", "update"))
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

@router.get("/{privilege_id}", response_model=PrivilegeResponse)
async def get_privilege(
    privilege_id: int,
    db: AsyncSession = Depends(get_db),
    user_data = Depends(require_privilege("privilege", "read"))
):
    privilege = await get_privilege_service(db, privilege_id)
    return {
        "success": True,
        "message": "Privilege retrieved successfully.",
        "data": {
            "id": privilege.id,
            "name": privilege.name,
            "action": privilege.action,
            "description": privilege.description
        }
    }

@router.get("/", response_model=PrivilegeListResponse)
async def get_all_privileges(
    offset: int = 0,
    limit: int = 6,
    db: AsyncSession = Depends(get_db),
    user_data = Depends(require_privilege("privilege", "read"))
):
    result = await get_all_privileges_service(db, offset, limit)
    
    return {
        "success": True,
        "message": "Privileges retrieved successfully.",
        "data": [
            {
                "id": privilege.id,
                "name": privilege.name,
                "action": privilege.action,
                "description": privilege.description
            }
            for privilege in result["items"]
        ],
        "total": result["total"],
        "offset": result["offset"],
        "limit": result["limit"],
        "has_more": result["has_more"]
    }

@router.post("/change-status/{privilege_id}", response_model=PrivilegeStatusResponse)
async def change_privilege_status(
    privilege_id: int,
    request: PrivilegeStatusRequest,
    db: AsyncSession = Depends(get_db),
    user_data = Depends(require_privilege("privilege", "update"))
):
    updated_privilege = await change_privilege_status_service(db, privilege_id, request)
    return {
        "success": True,
        "message": "Privilege status updated successfully.",
        "data": {
            "id": updated_privilege.id,
            "name": updated_privilege.name,
            "action": updated_privilege.action,
            "description": updated_privilege.description,
            "status_id": updated_privilege.status_id
        }
    }