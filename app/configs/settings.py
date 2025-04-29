from pydantic import ConfigDict
from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    SQLALCHEMY_DATABASE_URI: str
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SECRET_KEY: str

    model_config = ConfigDict(env_file=".env")

settings = Settings()
