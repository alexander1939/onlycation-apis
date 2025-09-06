from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime


class WalletCreateRequest(BaseModel):
    country: str = Field(default="MX", description="País de la cuenta Stripe")
    type: str = Field(default="express", description="Tipo de cuenta Stripe Connect")


class WalletUpdateRequest(BaseModel):
    # Campos de banco ya no son necesarios - Stripe maneja la información bancaria
    pass


class WalletResponse(BaseModel):
    id: int
    user_id: int
    stripe_account_id: Optional[str]
    stripe_bank_status: Optional[str]
    stripe_setup_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WalletBalanceResponse(BaseModel):
    stripe_balance: float
    stripe_currency: str
    pending_balance: float
    account_status: str
    stripe_dashboard_url: str


class AddFundsRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Cantidad (ya no se usa - Stripe maneja fondos)")
    description: Optional[str] = Field(None, description="Descripción de la transacción")


class WithdrawFundsRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Cantidad (ya no se usa - retiros via Stripe Dashboard)")
    description: Optional[str] = Field(None, description="Descripción del retiro")


class StripeConnectAccountRequest(BaseModel):
    country: str = Field(default="MX", description="País de la cuenta")
    type: str = Field(default="express", description="Tipo de cuenta Stripe Connect")


class DefaultResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
