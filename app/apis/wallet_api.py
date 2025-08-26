from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
import stripe
from app.apis.deps import get_db, auth_required
from app.schemas.wallets.wallet_schema import (
    WalletCreateRequest,
    WalletResponse,
    DefaultResponse
)
from app.services.wallets.wallet_service import WalletService

router = APIRouter()


@router.post("/create/", response_model=DefaultResponse)
async def create_wallet(
    wallet_data: WalletCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    """
    Crear una nueva cartera virtual para el docente autenticado.
    Automáticamente crea una cuenta de Stripe Connect.
    """
    wallet = await WalletService.create_wallet(db, user_data.get("user_id"), wallet_data)
    # Determinar mensaje según si es nueva o existente
    if wallet.stripe_bank_status == "pending":
        message = "Cartera lista. Completa la configuración en Stripe usando stripe_setup_url."
    else:
        message = "Cartera creada y configurada correctamente."
    
    return {
        "success": True,
        "message": message,
        "data": {
            "wallet_id": wallet.id,
            "stripe_account_id": wallet.stripe_account_id,
            "stripe_status": wallet.stripe_bank_status,
            "stripe_setup_url": wallet.stripe_setup_url
        }
    }


@router.get("/", response_model=DefaultResponse)
async def get_my_wallet(
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    """
    Obtener información completa de la cartera del docente autenticado.
    Incluye stripe_setup_url si está pendiente de configuración.
    """
    wallet = await WalletService.get_wallet_by_user_id(db, user_data.get("user_id"))
    if not wallet:
        raise HTTPException(status_code=404, detail="Cartera no encontrada")
    
    response_data = {
        "wallet_id": wallet.id,
        "stripe_account_id": wallet.stripe_account_id,
        "stripe_status": wallet.stripe_bank_status,
        "created_at": wallet.created_at.isoformat(),
        "updated_at": wallet.updated_at.isoformat()
    }
    
    # Si está pendiente, incluir el setup URL para completar configuración
    if wallet.stripe_bank_status == "pending" and wallet.stripe_setup_url:
        response_data["stripe_setup_url"] = wallet.stripe_setup_url
        message = "Cartera encontrada. Completa la configuración en Stripe usando stripe_setup_url."
    else:
        message = "Cartera encontrada y configurada correctamente."
    
    return {
        "success": True,
        "message": message,
        "data": response_data
    }


@router.get("/balance/", response_model=DefaultResponse)
async def get_wallet_balance(
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    """
    Obtener balance de Stripe Connect.
    Incluye stripe_setup_url si está pendiente o stripe_dashboard_url si está activo.
    """
    wallet = await WalletService.get_wallet_by_user_id(db, user_data.get("user_id"))
    if not wallet:
        raise HTTPException(status_code=404, detail="Cartera no encontrada")
    
    # Si está pendiente, devolver setup URL
    if wallet.stripe_bank_status == "pending" and wallet.stripe_setup_url:
        return {
            "success": True,
            "message": "Cartera pendiente de configuración. Usa stripe_setup_url para completar el proceso.",
            "data": {
                "stripe_account_id": wallet.stripe_account_id,
                "account_status": "pending",
                "stripe_setup_url": wallet.stripe_setup_url
            }
        }
    
    # Si está activo, obtener balance de Stripe
    balance_data = await WalletService.get_stripe_balance(db, user_data.get("user_id"))
    return {
        "success": True,
        "message": "Balance obtenido exitosamente. Usa stripe_dashboard_url para ver detalles en Stripe.",
        "data": balance_data
    }


@router.delete("/delete/", response_model=DefaultResponse)
async def delete_wallet(
    db: AsyncSession = Depends(get_db),
    user_data: dict = Depends(auth_required)
):
    """
    Eliminar cartera virtual (solo permitido si el saldo es 0).
    """
    await WalletService.delete_wallet(db, user_data.get("user_id"))
    return {
        "success": True,
        "message": "Cartera virtual eliminada exitosamente"
    }