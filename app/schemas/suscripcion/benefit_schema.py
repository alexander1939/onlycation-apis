"""
Modelo que representa la estructura de datos recibida y enviada en las APIs de beneficios
"""

from pydantic import BaseModel
from typing import Optional

# Schema para crear un beneficio
class CreateBenefitRequest(BaseModel):
    name: str
    description: Optional[str] = None

# Schema para actualizar un beneficio (todos los campos obligatorios)
class UpdateBenefitRequest(BaseModel):
    name: str
    description: Optional[str] = None
    status_id: int

# Schema para los datos de un beneficio
class BenefitData(BaseModel):
    name: str
    description: Optional[str] = None
    status_id: int

# Schema para respuesta de creación
class CreateBenefitResponse(BaseModel):
    success: bool
    message: str
    data: BenefitData

# Schema para respuesta de actualización
class UpdateBenefitResponse(BaseModel):
    success: bool
    message: str
    data: BenefitData 