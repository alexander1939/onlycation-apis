from app.configs.settings import settings
from passlib.context import CryptContext

SECRET_KEY = settings.SECRET_KEY

pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__default_rounds=12  
)

def get_password_hash(password: str) -> str:
    """Genera hash BCrypt seguro (soporta todos los caracteres)"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica contraseña contra hash almacenado"""
    return pwd_context.verify(plain_password, hashed_password)