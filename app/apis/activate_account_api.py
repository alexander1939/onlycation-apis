from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.apis.deps import auth_required, get_db
from app.schemas.teachers.activation_schema import (
    ActivationCheckResponse,
    ActivationCheckData,
    ActivationPerformResponse,
)
from app.services.teachers.activation_service import (
    check_teacher_activation_requirements,
    activate_teacher_account,
)

router = APIRouter()
security = HTTPBearer()


@router.get("/teacher/check", response_model=ActivationCheckResponse, dependencies=[Depends(auth_required)])
async def check_teacher_activation_route(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    token = credentials.credentials
    try:
        result = await check_teacher_activation_requirements(db, token)
        return ActivationCheckResponse(
            success=True,
            message="Requisitos de activación consultados correctamente",
            data=ActivationCheckData(**result),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error al consultar requisitos de activación")


@router.post("/teacher/activate", response_model=ActivationPerformResponse, dependencies=[Depends(auth_required)])
async def perform_teacher_activation_route(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    token = credentials.credentials
    try:
        result = await activate_teacher_account(db, token)
        return ActivationPerformResponse(
            success=True,
            message="Cuenta de docente activada correctamente",
            data=ActivationCheckData(**result),
        )
    except ValueError as e:
        # Si faltan requisitos o usuario/status inexistente
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error al activar la cuenta del docente")