from pydantic import BaseModel
from typing import List


class ActivationCheckData(BaseModel):
    has_preference: bool
    has_price: bool
    has_wallet: bool
    has_video: bool
    has_documents: bool
    missing: List[str]


class ActivationCheckResponse(BaseModel):
    success: bool
    message: str
    data: ActivationCheckData


class ActivationPerformResponse(BaseModel):
    success: bool
    message: str
    data: ActivationCheckData
