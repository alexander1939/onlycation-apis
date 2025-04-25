en el archivo de alembic.ini se debe de poner la ruta de la debe
sqlalchemy.url = sqlite:///task.db 

No subir .env y alembic.ini subir comando de alembic


uvicorn app.main:app --reload