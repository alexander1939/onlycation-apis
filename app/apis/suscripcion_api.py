from fastapi import APIRouter, Depends, Query, HTTPException, Request
from app.schemas.suscripcion.payment_subscriptions_schema import (
    SubscribeRequest, SubscribeResponse,
    VerifyPaymentResponse, WebhookResponse
)
from app.schemas.suscripcion.plan_schema import CreatePlanRequest, CreatePlanResponse, UpdatePlanRequest, UpdatePlanResponse, GetPlansResponse, GetPlanResponse
from app.schemas.suscripcion.benefit_schema import CreateBenefitRequest, CreateBenefitResponse, UpdateBenefitRequest, UpdateBenefitResponse, GetBenefitsResponse, GetBenefitResponse
from app.services.suscripcion.payment_subscriptions_service import (
    subscribe_user_to_plan, 
    create_subscription_session, 
    verify_payment_and_create_subscription,
    handle_stripe_webhook,
    get_user_by_token
)
from app.services.suscripcion.plan_service import create_plan, update_plan, get_all_plans, get_plan_by_id
from app.services.suscripcion.benefit_service import create_benefit, update_benefit, get_all_benefits, get_benefit_by_id
from app.apis.deps import auth_required, get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

# Endpoints para Planes
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

@router.get("/plans/", response_model=GetPlansResponse, dependencies=[Depends(auth_required)])
async def get_plans_route(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_db)
):
    plans = await get_all_plans(db, skip, limit)
    return {
        "success": True,
        "message": "Plans retrieved successfully",
        "data": [
            {
                "name": plan.name, # type: ignore
                "price": plan.price, # type: ignore
                "duration": plan.duration, # type: ignore
                "role_id": plan.role_id # type: ignore
            } for plan in plans # type: ignore
        ]
    }

@router.get("/plans/{plan_id}", response_model=GetPlanResponse, dependencies=[Depends(auth_required)])
async def get_plan_route(plan_id: int, db: AsyncSession = Depends(get_db)):
    plan = await get_plan_by_id(db, plan_id)
    return {
        "success": True,
        "message": "Plan retrieved successfully",
        "data": {
            "guy": plan.guy, # type: ignore
            "name": plan.name, # type: ignore
            "description": plan.description, # type: ignore
            "price": plan.price, # type: ignore
            "duration": plan.duration, # type: ignore
            "role_id": plan.role_id, # type: ignore
            "status_id": plan.status_id, # type: ignore
            "created_at": plan.created_at.isoformat(), # type: ignore
            "updated_at": plan.updated_at.isoformat() # type: ignore
        }
    }

# Endpoints para Beneficios
@router.post("/benefits/", response_model=CreateBenefitResponse, dependencies=[Depends(auth_required)])
async def create_benefit_route(request: CreateBenefitRequest, db: AsyncSession = Depends(get_db)):
    benefit = await create_benefit(db, request)
    return {
        "success": True,
        "message": "Benefit created successfully",
        "data": {
            "name": benefit.name, # type: ignore
            "description": benefit.description, # type: ignore
            "status_id": benefit.status_id # type: ignore
        }
    }

@router.put("/benefits/{benefit_id}", response_model=UpdateBenefitResponse, dependencies=[Depends(auth_required)])
async def update_benefit_route(benefit_id: int, request: UpdateBenefitRequest, db: AsyncSession = Depends(get_db)):
    benefit = await update_benefit(db, benefit_id, request)
    return {
        "success": True,
        "message": "Benefit updated successfully",
        "data": {
            "name": benefit.name, # type: ignore
            "description": benefit.description, # type: ignore
            "status_id": benefit.status_id # type: ignore
        }
    }

@router.get("/benefits/", response_model=GetBenefitsResponse, dependencies=[Depends(auth_required)])
async def get_benefits_route(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_db)
):
    benefits = await get_all_benefits(db, skip, limit)
    return {
        "success": True,
        "message": "Benefits retrieved successfully",
        "data": [
            {
                "name": benefit.name, # type: ignore
                "description": benefit.description, # type: ignore
                "status_id": benefit.status_id # type: ignore
            } for benefit in benefits # type: ignore
        ]
    }

@router.get("/benefits/{benefit_id}", response_model=GetBenefitResponse, dependencies=[Depends(auth_required)])
async def get_benefit_route(benefit_id: int, db: AsyncSession = Depends(get_db)):
    benefit = await get_benefit_by_id(db, benefit_id)
    return {
        "success": True,
        "message": "Benefit retrieved successfully",
        "data": {
            "name": benefit.name, # type: ignore
            "description": benefit.description, # type: ignore
            "status_id": benefit.status_id, # type: ignore
            "created_at": benefit.created_at.isoformat(), # type: ignore
            "updated_at": benefit.updated_at.isoformat() # type: ignore
        }
    }

@router.post("/crear-suscripcion", response_model=SubscribeResponse)
async def crear_suscripcion(
    request: SubscribeRequest,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    """
    Crea una sesión de checkout de Stripe para suscripción
    """
    user = await get_user_by_token(db, user_data.get("user_id"))
    result = await create_subscription_session(db, user, request.plan_id)
    
    return {
        "success": True,
        "message": "Sesión de pago creada exitosamente",
        "data": {
            "url": result["url"],
            "session_id": result["session_id"],
            "plan_name": result["plan_name"],
            "plan_price": result["plan_price"]
        }
    }

@router.get("/verificar-pago/{session_id}", response_model=VerifyPaymentResponse)
async def verificar_pago(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    """
    Verifica el estado del pago y guarda en la base de datos si fue exitoso
    """
    result = await verify_payment_and_create_subscription(db, session_id, user_data.get("user_id"))
    
    return {
        "success": result["success"],
        "message": result["message"],
        "payment_status": result.get("payment_status"),
        "data": result.get("data")
    }

@router.post("/webhook/stripe", response_model=WebhookResponse)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook para procesar eventos de Stripe
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    result = await handle_stripe_webhook(db, payload, sig_header)
    
    return {
        "success": result["success"],
        "message": "Webhook procesado correctamente"
    } 


