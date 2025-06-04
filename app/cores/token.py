from datetime import datetime, timedelta, UTC
from fastapi import HTTPException
from jose import JWTError, jwt
import os

SECRET_KEY = os.getenv("SECRET_KEY", "clave_supersecreta")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


""" 
Genera un token JWT codificado con la información proporcionada en `data`.
    - `expires_delta` permite especificar tiempo de expiración personalizado.
    - Si no se pasa, se usa el tiempo por defecto (24 horas).
    - El token incluye la clave de expiración "exp" para validar su vigencia.
"""
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"type": "access", "exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"type": "refresh", "exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
