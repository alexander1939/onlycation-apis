
from fastapi import APIRouter, Depends
from app.apis.deps import get_db, require_privilege
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.schemas.auths.login_schema import LoginRequest, LoginResponse
from app.schemas.privileges.privilege_shema import PrivilegeCreateRequest, PrivilegeResponse
from app.services.auths.login_service import login_user
from app.services.privileges.privilege_service import create_privilege_service


from fastapi import APIRouter, HTTPException


router = APIRouter()

# Define la dependencia de privilegio
privilege_create_dependency = require_privilege("privilege", "create")

@router.post("/create/", response_model=PrivilegeResponse)
async def create_privilege(
    request: PrivilegeCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(privilege_create_dependency)  # Protección con privilegio
):
    new_privilege = await create_privilege_service(db, request)
    return {
        "success": True,
        "message": "Privilegio creado exitosamente.",
        "data": {
            "id": new_privilege.id,
            "name": new_privilege.name,
            "action": new_privilege.action,
            "description": new_privilege.description
        }
    }