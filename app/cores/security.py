from app.configs.settings import settings
from passlib.context import CryptContext

SECRET_KEY = settings.SECRET_KEY


""" 
Configura el contexto de hashing usando el algoritmo BCrypt.
Este contexto se usa internamente para hashear y verificar contraseñas.
"""
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__default_rounds=12  
)


""" 
Genera un hash seguro de la contraseña usando BCrypt.
Se utiliza al registrar o actualizar contraseñas antes de guardarlas en la base de datos.
"""
def get_password_hash(password: str) -> str:
    """Genera hash BCrypt seguro (soporta todos los caracteres)"""
    return pwd_context.hash(password)


""" 
Verifica si una contraseña en texto plano coincide con un hash previamente generado.
Se usa principalmente durante el login para validar credenciales del usuario.
"""

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica contraseña contra hash almacenado"""
    return pwd_context.verify(plain_password, hashed_password)