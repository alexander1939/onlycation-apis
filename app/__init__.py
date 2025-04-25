from fastapi import FastAPI
from app.core.db import Base, engine
from app.apis.routes import user
from app.models.common.status import Status

def create_app() -> FastAPI:

    Base.metadata.create_all(bind=engine)

    app = FastAPI(title="onlyCation")

    ##app.include_router(user.router, prefix="/api/users", tags=["Usuarios"])

    return app
