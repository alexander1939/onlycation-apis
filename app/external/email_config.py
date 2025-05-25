"""
Configuración para enviar correos electrónicos usando FastAPI-Mail.
Carga los parámetros desde la configuración global de la aplicación.
"""

from fastapi_mail import ConnectionConfig
from app.configs.settings import settings


"""
Configura la conexión al servidor SMTP con las credenciales y parámetros de seguridad.
Incluye:
  - Usuario y contraseña para autenticación.
  - Datos del servidor y puerto.
  - Uso de TLS o SSL según configuración.
  - Validación del certificado SSL para seguridad.
"""
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)