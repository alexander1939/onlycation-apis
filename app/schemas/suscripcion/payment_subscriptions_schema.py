from pydantic import BaseModel
from typing import Optional, List

class SubscribeRequest(BaseModel):
    plan_guy: str

class SubscribeResponse(BaseModel):
    success: bool
    message: str
    data: dict  # contiene checkout_url y opcional subscription_id
