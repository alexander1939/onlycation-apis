from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.teachers.price_schema import (
    PriceCreateRequest,
    PriceCreateResponse,
    PriceCreateData,
    PriceReadResponse,
    PriceAvailabilityResponse,
    PriceAvailabilityData,
    PriceRangeItem,
)
from app.services.teachers.price_service import (
    create_price_by_token,
    get_prices_by_token,
    get_price_availability_by_token,
)
from app.apis.deps import auth_required, get_db


router = APIRouter()
security = HTTPBearer()

@router.post("/create/", response_model=PriceCreateResponse, dependencies=[Depends(auth_required)])
async def create_price_route(
    price_data: PriceCreateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    try:
        price = await create_price_by_token(db, token, price_data)

        return PriceCreateResponse(
            success=True,
            message="Precio registrado exitosamente",
            data=PriceCreateData(
                id=price.id,
                preference_id=price.preference_id,
                price_range_id=price.price_range_id,
                selected_prices=price.selected_prices,
                extra_hour_price=price.extra_hour_price,
                created_at=price.created_at
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error en la base de datos")

@router.get("/list/", response_model=PriceReadResponse, dependencies=[Depends(auth_required)])
async def get_prices_route(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    try:
        prices = await get_prices_by_token(db, token)

        return PriceReadResponse(
            success=True,
            message="Precios obtenidos correctamente",
            data=[
                PriceCreateData(
                    id=p.id,
                    preference_id=p.preference_id,
                    price_range_id=p.price_range_id,
                    selected_prices=p.selected_prices,
                    extra_hour_price=p.extra_hour_price,
                    created_at=p.created_at
                ) for p in prices
            ]
        )
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error al consultar los precios")

@router.get("/availability/", response_model=PriceAvailabilityResponse, dependencies=[Depends(auth_required)])
async def get_price_availability_route(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """
    Devuelve, para el docente autenticado (por token), su `preference_id`,
    el `educational_level_id` de esa preferencia y la lista de `price_ranges`
    disponibles para ese nivel educativo.
    """
    token = credentials.credentials
    try:
        result = await get_price_availability_by_token(db, token)

        return PriceAvailabilityResponse(
            success=True,
            message="Disponibilidad de precios obtenida correctamente",
            data=PriceAvailabilityData(
                preference_id=result["preference_id"],
                educational_level_id=result["educational_level_id"],
                price_ranges=[
                    PriceRangeItem(**r) for r in result.get("price_ranges", [])
                ],
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error al consultar la disponibilidad de precios")
