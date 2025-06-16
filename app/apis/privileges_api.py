
from fastapi import APIRouter, Depends
from app.apis.deps import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.schemas.auths.login_schema import LoginRequest, LoginResponse
from app.services.auths.login_service import login_user


from fastapi import APIRouter, HTTPException

router = APIRouter()