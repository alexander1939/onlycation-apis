en el archivo de alembic.ini se debe de poner la ruta de la debe
sqlalchemy.url = sqlite:///task.db 

No subir .env y alembic.ini subir comando de alembic


uvicorn app.main:app --reload

primero es crear tu entorno virtual con 
python -m venv .venv

activa tu entorno virtual con 
source venv/bin/activate

instala los requerientos 
pip install -r  requirements.txt 

copia y remnombra el archivo de .envExample a .env