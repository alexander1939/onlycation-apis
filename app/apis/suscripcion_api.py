from fastapi import APIRouter, Depends
from app.schemas.suscripcion.plan_schema import CreatePlanRequest, CreatePlanResponse, UpdatePlanRequest, UpdatePlanResponse
from app.services.suscripcion.plan_service import create_plan, update_plan
from app.apis.deps import auth_required, get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.post("/plans/", response_model=CreatePlanResponse, dependencies=[Depends(auth_required)])
async def create_plan_route(request: CreatePlanRequest, db: AsyncSession = Depends(get_db)):
    plan = await create_plan(db, request)
    return {
        "success": True,
        "message": "Plan created successfully",
        "data": {
            "guy": plan.guy, # type: ignore
            "name": plan.name, # type: ignore
            "description": plan.description,   # type: ignore
            "price": plan.price, # type: ignore
            "duration": plan.duration, # type: ignore
            "role_id": plan.role_id, # type: ignore
            "status_id": plan.status_id # type: ignore
        }
    }

@router.put("/plans/{plan_id}", response_model=UpdatePlanResponse, dependencies=[Depends(auth_required)])
async def update_plan_route(plan_id: int, request: UpdatePlanRequest, db: AsyncSession = Depends(get_db)):
    plan = await update_plan(db, plan_id, request)
    return {
        "success": True,
        "message": "Plan updated successfully",
        "data": {
            "guy": plan.guy, # type: ignore
            "name": plan.name, # type: ignore
            "description": plan.description, # type: ignore
            "price": plan.price, # type: ignore
            "duration": plan.duration, # type: ignore
            "role_id": plan.role_id, # type: ignore
            "status_id": plan.status_id # type: ignore
        }
    } 