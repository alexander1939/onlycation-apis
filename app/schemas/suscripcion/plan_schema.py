"""
Modelo que representa la estructura de datos recibida y enviada en las APIs de planes
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Schema para crear un plan
class CreatePlanRequest(BaseModel):
    guy: str
    name: str
    description: Optional[str] = None
    price: int
    duration: str
    role_id: int

# Schema para actualizar un plan (todos los campos obligatorios)
class UpdatePlanRequest(BaseModel):
    guy: str
    name: str
    description: Optional[str] = None
    price: int
    duration: str
    role_id: int
    status_id: int

# Schema para los datos de un plan
class PlanData(BaseModel):
    guy: str
    name: str
    description: Optional[str] = None
    price: int
    duration: str
    role_id: int
    status_id: int

# Schema para datos simplificados de un plan (solo consulta)
class PlanSimpleData(BaseModel):
    name: str
    price: int
    duration: Optional[str] = None
    role_id: int

# Schema para datos completos de un plan (sin ID)
class PlanCompleteData(BaseModel):
    guy: str
    name: str
    description: Optional[str] = None
    price: int
    duration: Optional[str] = None
    role_id: int
    status_id: int
    created_at: str
    updated_at: str

# Schema para respuesta de creación
class CreatePlanResponse(BaseModel):
    success: bool
    message: str
    data: PlanData

# Schema para respuesta de actualización
class UpdatePlanResponse(BaseModel):
    success: bool
    message: str
    data: PlanData

# Schema para respuesta de listado
class GetPlansResponse(BaseModel):
    success: bool
    message: str
    data: List[PlanSimpleData]

# Schema para respuesta de plan específico
class GetPlanResponse(BaseModel):
    success: bool
    message: str
    data: PlanCompleteData 


class SubscriptionData(BaseModel):
    subscription_id: int
    plan_id: int
    plan_name: str
    plan_description: Optional[str] = None
    price: float
    start_date: datetime
    end_date: Optional[datetime] = None
    status: str
    days_left: Optional[int] = None

# Schema para respuesta de "mi suscripción"
class MySubscriptionResponse(BaseModel):
    success: bool
    message: str
    data: SubscriptionData