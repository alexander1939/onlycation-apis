# OnyCation-apis

> [!TIP]
> Usa como convención `.venv` para tu entorno virtual.

> [!WARNING]
> No subas archivos sensibles como `.env` o `alembic.ini`. En su lugar, sube solo los comandos de Alembic necesarios(sqlalchemy.url = sqlite:///task.db ).

> [!CAUTION]
> No modifiques el archivo `.gitignore` sin autorización previa.

> [!NOTE]
> Copia el archivo `envExplate` y renómbralo como `.env` para configurar tu entorno.

> [!IMPORTANT]
> No elimines el archivo `envExplate`, ya que otros desarrolladores lo necesitan como base.

> [!IMPORTANT]
> Ejecuta los tests disponibles para asegurarte de que las APIs funcionen correctamente.


## 🧑‍💻 **Instrucciones para correr el proyecto**

### Instalación del proyecto
Clonar el repositorio
```bash
git clone https://github.com/alexander1939/onlycation-apis.git
```
Entrar en el proyecto
```bash
cd onlycation-apis
```
Crea tu entorno virtua
```bash
python -m venv .venv
```
Enciende tu entorno virtual
```bash
source venv/bin/activate
```
Instalar Requerimientos
```bash
pip install -r  requirements.txt 
```
Ejecutar el proyecto

```bash
uvicorn app.main:app --reload
```

```bash
python - << 'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
```