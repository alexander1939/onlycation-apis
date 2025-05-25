from pydantic import ConfigDict, EmailStr
from pydantic_settings import BaseSettings

"""
Se carga automáticamente desde el archivo `.env` o las variables de entorno del sistema.
    - Define y carga la configuración principal de la aplicación desde variables de entorno.
    - Incluye parámetros para la base de datos, seguridad y configuración del correo electrónico.
    - Configuracion global
"""
class Settings(BaseSettings):
    SQLALCHEMY_DATABASE_URI: str
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SECRET_KEY: str

    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_STARTTLS: bool
    MAIL_SSL_TLS: bool

    model_config = ConfigDict(env_file=".env")


settings = Settings()
