import stripe
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from typing import Optional
from decimal import Decimal

from app.models.teachers.wallet import Wallet
from app.models.users.user import User
from app.schemas.wallets.wallet_schema import (
    WalletCreateRequest, 
    WalletUpdateRequest,
    AddFundsRequest,
    WithdrawFundsRequest,
    StripeConnectAccountRequest
)
from app.external.stripe_config import stripe_config


class WalletService:
    
    @staticmethod
    async def create_wallet(db: AsyncSession, user_id: int, wallet_data: WalletCreateRequest) -> Wallet:
        """Crear una nueva cartera virtual para un docente"""
        
        # Verificar que el usuario existe y es docente
        from app.models.common.role import Role
        result = await db.execute(
            select(User, Role)
            .join(Role, User.role_id == Role.id)
            .where(User.id == user_id)
        )
        user_role = result.first()
        
        if not user_role:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        user, role = user_role
        if role.name != "teacher":
            raise HTTPException(status_code=403, detail="Solo los docentes pueden crear carteras")
        
        # Verificar si ya tiene una cartera
        existing_wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
        existing_wallet = existing_wallet_result.scalar_one_or_none()
        
        if existing_wallet:
            # Si ya tiene cartera pero está pendiente, generar nuevo setup URL
            if existing_wallet.stripe_bank_status == "pending" and existing_wallet.stripe_account_id:
                try:
                    # Crear nuevo enlace de configuración
                    account_link = stripe.AccountLink.create(
                        account=existing_wallet.stripe_account_id,
                        return_url="http://localhost:5173/",  # Cambia por tu URL
                        refresh_url="http://localhost:5173/", # Cambia por tu URL
                        type='account_onboarding',
                    )
                    
                    # Actualizar el setup URL
                    existing_wallet.stripe_setup_url = account_link.url
                    await db.commit()
                    await db.refresh(existing_wallet)
                    
                    return existing_wallet
                    
                except stripe.error.StripeError as e:
                    raise HTTPException(status_code=400, detail=f"Error al generar nuevo enlace: {str(e)}")
            else:
                raise HTTPException(status_code=400, detail="El docente ya tiene una cartera configurada")
        
        # Crear cuenta de Stripe Connect automáticamente
        try:
            stripe_account = stripe.Account.create(
                type=wallet_data.type,
                country=wallet_data.country,
                capabilities={
                    'transfers': {'requested': True},
                }
            )
            
            # Crear enlace de configuración
            account_link = stripe.AccountLink.create(
                account=stripe_account.id,
                return_url="http://localhost:5173/",  # Cambia por tu URL
                refresh_url="http://localhost:5173/", # Cambia por tu URL
                type='account_onboarding',
            )
            
            # Crear la cartera con la cuenta de Stripe
            wallet = Wallet(
                user_id=user_id,
                stripe_account_id=stripe_account.id,
                stripe_bank_status="pending",  # Pendiente hasta completar onboarding
                stripe_setup_url=account_link.url
            )
            
            db.add(wallet)
            await db.commit()
            await db.refresh(wallet)
            
            return wallet
            
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=400, detail=f"Error al crear cuenta de Stripe: {str(e)}")
    
    @staticmethod
    async def get_wallet_by_user_id(db: AsyncSession, user_id: int) -> Optional[Wallet]:
        """Obtener cartera por ID de usuario"""
        result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_stripe_balance(db: AsyncSession, user_id: int) -> dict:
        """Obtener balance de la cuenta de Stripe Connect"""
        wallet = await WalletService.get_wallet_by_user_id(db, user_id)
        
        if not wallet:
            raise HTTPException(status_code=404, detail="Cartera no encontrada")
        
        if not wallet.stripe_account_id:
            raise HTTPException(status_code=400, detail="Cuenta de Stripe no encontrada")
        
        try:
            # Obtener balance de Stripe
            balance = stripe.Balance.retrieve(stripe_account=wallet.stripe_account_id)
            
            # Obtener estado de la cuenta
            account = stripe.Account.retrieve(wallet.stripe_account_id)
            
            # Crear link del dashboard de Stripe Express
            dashboard_link = stripe.Account.create_login_link(wallet.stripe_account_id)
            
            # Actualizar estado en BD si cambió
            if account.charges_enabled and wallet.stripe_bank_status != "active":
                wallet.stripe_bank_status = "active"
                db.add(wallet)
                await db.commit()
            
            # Procesar balance disponible
            available_balance = 0.00
            pending_balance = 0.00
            currency = "mxn"
            
            if balance.available:
                for bal in balance.available:
                    if bal.currency == "mxn":
                        available_balance = bal.amount / 100
                        currency = bal.currency
                        break
            
            if balance.pending:
                for bal in balance.pending:
                    if bal.currency == "mxn":
                        pending_balance = bal.amount / 100
                        break
            
            return {
                "stripe_balance": available_balance,
                "stripe_currency": currency,
                "pending_balance": pending_balance,
                "account_status": "active" if account.charges_enabled else "pending",
                "stripe_dashboard_url": dashboard_link.url  # Link para ver balance en Stripe
            }
            
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=400, detail=f"Error al obtener balance: {str(e)}")
    
    @staticmethod
    async def check_and_update_stripe_status(db: AsyncSession, user_id: int) -> Wallet:
        """Verificar y actualizar estado de cuenta Stripe"""
        wallet = await WalletService.get_wallet_by_user_id(db, user_id)
        
        if not wallet or not wallet.stripe_account_id:
            raise HTTPException(status_code=404, detail="Cartera o cuenta Stripe no encontrada")
        
        try:
            account = stripe.Account.retrieve(wallet.stripe_account_id)
            
            # Actualizar estado
            new_status = "active" if account.charges_enabled else "pending"
            if wallet.stripe_bank_status != new_status:
                wallet.stripe_bank_status = new_status
                db.add(wallet)
                await db.commit()
                await db.refresh(wallet)
            
            return wallet
            
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=400, detail=f"Error al verificar cuenta: {str(e)}")
    
    @staticmethod
    async def update_wallet(db: AsyncSession, user_id: int, wallet_data: WalletUpdateRequest) -> Wallet:
        """Actualizar información de la cartera"""
        wallet = await WalletService.get_wallet_by_user_id(db, user_id)
        
        if not wallet:
            raise HTTPException(status_code=404, detail="Cartera no encontrada")
        
        # No hay campos de banco para actualizar ya que usamos solo Stripe
        # Este método puede ser removido o usado para otros campos en el futuro
        pass
        
        await db.commit()
        await db.refresh(wallet)
        
        return wallet
    
    @staticmethod
    async def add_funds(db: AsyncSession, user_id: int, add_funds_data: AddFundsRequest) -> Wallet:
        """Los fondos ahora se manejan directamente en Stripe, este método ya no es necesario"""
        raise HTTPException(status_code=400, detail="Los fondos se manejan directamente en Stripe Connect. Use la API de Stripe para transferencias.")
    
    @staticmethod
    async def create_stripe_connect_account(db: AsyncSession, user_id: int, account_data: StripeConnectAccountRequest) -> Wallet:
        """Crear cuenta de Stripe Connect para el docente"""
        wallet = await WalletService.get_wallet_by_user_id(db, user_id)
        
        if not wallet:
            raise HTTPException(status_code=404, detail="Cartera no encontrada")
        
        if wallet.stripe_account_id:
            raise HTTPException(status_code=400, detail="Ya existe una cuenta de Stripe Connect")
        
        try:
            # Crear cuenta de Stripe Connect
            account = stripe.Account.create(
                type=account_data.type,
                country=account_data.country,
                capabilities={
                    'transfers': {'requested': True},
                }
            )
            
            # Actualizar la cartera con el ID de Stripe
            wallet.stripe_account_id = account.id
            wallet.stripe_bank_status = "pending"
            
            await db.commit()
            await db.refresh(wallet)
            
            return wallet
            
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=400, detail=f"Error al crear cuenta de Stripe: {str(e)}")
    
    @staticmethod
    async def create_account_link(db: AsyncSession, user_id: int, return_url: str, refresh_url: str) -> str:
        """Crear enlace de configuración de cuenta para Stripe Connect"""
        wallet = await WalletService.get_wallet_by_user_id(db, user_id)
        
        if not wallet or not wallet.stripe_account_id:
            raise HTTPException(status_code=404, detail="Cuenta de Stripe Connect no encontrada")
        
        try:
            account_link = stripe.AccountLink.create(
                account=wallet.stripe_account_id,
                return_url=return_url,
                refresh_url=refresh_url,
                type='account_onboarding',
            )
            
            return account_link.url
            
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=400, detail=f"Error al crear enlace de cuenta: {str(e)}")
    
    @staticmethod
    async def check_stripe_account_status(db: AsyncSession, user_id: int) -> Wallet:
        """Verificar el estado de la cuenta de Stripe Connect"""
        wallet = await WalletService.get_wallet_by_user_id(db, user_id)
        
        if not wallet or not wallet.stripe_account_id:
            raise HTTPException(status_code=404, detail="Cuenta de Stripe Connect no encontrada")
        
        try:
            account = stripe.Account.retrieve(wallet.stripe_account_id)
            
            # Actualizar estado basado en la información de Stripe
            if account.details_submitted and account.charges_enabled:
                wallet.stripe_bank_status = "active"
            elif account.details_submitted:
                wallet.stripe_bank_status = "pending_verification"
            else:
                wallet.stripe_bank_status = "pending"
            
            await db.commit()
            await db.refresh(wallet)
            
            return wallet
            
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=400, detail=f"Error al verificar cuenta de Stripe: {str(e)}")
    
    @staticmethod
    async def withdraw_funds(db: AsyncSession, user_id: int, withdraw_data: WithdrawFundsRequest) -> Wallet:
        """Retirar fondos de la cartera virtual a Stripe Connect"""
        wallet = await WalletService.get_wallet_by_user_id(db, user_id)
        
        if not wallet:
            raise HTTPException(status_code=404, detail="Cartera no encontrada")
        
        if not wallet.stripe_account_id:
            raise HTTPException(status_code=400, detail="Cuenta de Stripe Connect no configurada")
        
        if wallet.stripe_bank_status != "active":
            raise HTTPException(status_code=400, detail="Cuenta de Stripe Connect no está activa")
        
        # Los retiros ahora se manejan directamente desde Stripe Dashboard
        raise HTTPException(status_code=400, detail="Los retiros se manejan directamente desde el Stripe Dashboard. Use el enlace del dashboard para gestionar pagos.")
    
    @staticmethod
    async def get_wallet_balance(db: AsyncSession, user_id: int) -> Wallet:
        """Obtener balance actual de la cartera"""
        wallet = await WalletService.get_wallet_by_user_id(db, user_id)
        
        if not wallet:
            raise HTTPException(status_code=404, detail="Cartera no encontrada")
        
        return wallet
    
    @staticmethod
    async def delete_wallet(db: AsyncSession, user_id: int) -> bool:
        """Eliminar cartera (solo si el saldo es 0)"""
        wallet = await WalletService.get_wallet_by_user_id(db, user_id)
        
        if not wallet:
            raise HTTPException(status_code=404, detail="Cartera no encontrada")
        
        # Verificar que no haya balance pendiente en Stripe
        try:
            balance = stripe.Balance.retrieve(stripe_account=wallet.stripe_account_id)
            has_balance = False
            
            if balance.available:
                for bal in balance.available:
                    if bal.amount > 0:
                        has_balance = True
                        break
            
            if has_balance:
                raise HTTPException(status_code=400, detail="No se puede eliminar una cartera con saldo en Stripe")
                
        except stripe.error.StripeError:
            # Si no se puede verificar el balance, no permitir eliminación
            raise HTTPException(status_code=400, detail="No se puede verificar el balance de Stripe")
        
        await db.delete(wallet)
        await db.commit()
        
        return True
